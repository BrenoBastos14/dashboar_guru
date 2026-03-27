"use client";

import { useState, useRef, useCallback, DragEvent, ChangeEvent } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface AnalysisResult {
  hook_visual?: {
    descricao?: string;
    elementos?: string[];
    avaliacao?: string;
    justificativa?: string;
  };
  formato?: {
    tipo?: string;
    descricao?: string;
  };
  presenca_humana?: {
    tem_rosto?: boolean;
    tipo?: string;
    descricao?: string;
  };
  texto_em_tela?: {
    tem_texto?: boolean;
    tipos?: string[];
    descricao?: string;
  };
  cores_dominantes?: {
    cores?: string[];
    estilo_visual?: string;
  };
  edicao?: {
    ritmo?: string;
    transicoes?: string;
    cortes_por_minuto_estimado?: string;
    descricao?: string;
  };
  cta_visual?: {
    tem_cta?: boolean;
    tipo?: string;
    descricao?: string;
  };
  pontos_fortes?: string[];
  pontos_fracos?: string[];
  sugestoes?: string[];
  nota_geral?: {
    score?: string;
    justificativa?: string;
  };
  raw?: string;
}

type Step = "idle" | "uploading" | "transcribing" | "analyzing" | "done" | "error";
type InputMode = "video" | "images";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getScoreColor(score: number) {
  if (score >= 8) return "#22c55e";
  if (score >= 5) return "#eab308";
  return "#ef4444";
}

function getAvaliacaoBadge(avaliacao?: string) {
  if (!avaliacao) return "badge-default";
  const a = avaliacao.toLowerCase();
  if (a === "forte") return "badge-forte";
  if (a === "médio" || a === "medio") return "badge-medio";
  if (a === "fraco") return "badge-fraco";
  return "badge-default";
}

function StepIcon({ state }: { state: "active" | "done" | "pending" }) {
  if (state === "done") {
    return (
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
        <circle cx="9" cy="9" r="9" fill="rgba(34,197,94,0.2)" />
        <path d="M5 9l3 3 5-5" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (state === "active") return <div className="spinner" />;
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="8" stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" />
    </svg>
  );
}

function ListItems({ items, color }: { items: string[]; color: string }) {
  return (
    <div>
      {items.map((item, i) => (
        <div key={i} className="list-item">
          <div className="list-bullet" style={{ background: color }} />
          <span>{item}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Upload Zone ─────────────────────────────────────────────────────────────

function DropZone({
  mode,
  onFiles,
  disabled,
}: {
  mode: InputMode;
  onFiles: (files: File[]) => void;
  disabled: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      const files = Array.from(e.dataTransfer.files);
      onFiles(files);
    },
    [disabled, onFiles]
  );

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) onFiles(Array.from(e.target.files));
  };

  const isVideo = mode === "video";

  return (
    <div
      className={`drop-zone rounded-xl p-8 flex flex-col items-center justify-center gap-4 cursor-pointer ${dragging ? "drag-over" : ""} ${disabled ? "opacity-40 pointer-events-none" : ""}`}
      style={{ minHeight: 200 }}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <div
        className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl"
        style={{ background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.3)" }}
      >
        {isVideo ? "🎬" : "🖼️"}
      </div>
      <div className="text-center">
        <p className="font-semibold text-white mb-1">
          {isVideo ? "Arraste um vídeo aqui" : "Arraste imagens aqui"}
        </p>
        <p className="text-sm" style={{ color: "rgba(255,255,255,0.4)" }}>
          {isVideo ? "MP4, MOV, WEBM · máx. 50MB" : "JPG, PNG, WEBP · múltiplas imagens"}
        </p>
      </div>
      <button
        type="button"
        className="px-4 py-2 rounded-lg text-sm font-semibold gradient-bg text-white"
        style={{ pointerEvents: "none" }}
      >
        Selecionar {isVideo ? "vídeo" : "imagens"}
      </button>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={isVideo ? "video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm" : "image/*"}
        multiple={!isVideo}
        onChange={handleChange}
      />
    </div>
  );
}

// ─── Results ─────────────────────────────────────────────────────────────────

function ResultsView({ analysis, transcription }: { analysis: AnalysisResult; transcription?: string }) {
  const score = parseInt(analysis.nota_geral?.score || "0") || 0;
  const scoreColor = getScoreColor(score);

  const exportReport = () => {
    const lines: string[] = [
      "=== RELATÓRIO DE ANÁLISE DE CRIATIVO — ALPHA MEDIA ===",
      "",
      `NOTA GERAL: ${score}/10`,
      analysis.nota_geral?.justificativa || "",
      "",
    ];
    if (transcription) {
      lines.push("TRANSCRIÇÃO:", transcription, "");
    }
    lines.push(
      `HOOK VISUAL: ${analysis.hook_visual?.avaliacao || ""}`,
      analysis.hook_visual?.descricao || "",
      "",
      `FORMATO: ${analysis.formato?.tipo || ""}`,
      analysis.formato?.descricao || "",
      "",
      `PRESENÇA HUMANA: ${analysis.presenca_humana?.tem_rosto ? "Sim" : "Não"} — ${analysis.presenca_humana?.tipo || ""}`,
      "",
      "PONTOS FORTES:",
      ...(analysis.pontos_fortes || []).map((p) => `• ${p}`),
      "",
      "PONTOS FRACOS:",
      ...(analysis.pontos_fracos || []).map((p) => `• ${p}`),
      "",
      "SUGESTÕES:",
      ...(analysis.sugestoes || []).map((p) => `• ${p}`),
    );
    navigator.clipboard.writeText(lines.join("\n")).then(() => {
      alert("Relatório copiado para a área de transferência!");
    });
  };

  return (
    <div className="animate-fade-in space-y-6">
      {/* Score */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="section-title mb-1">Nota Geral</p>
            <div className="flex items-end gap-2">
              <span className="text-5xl font-bold" style={{ color: scoreColor }}>{score}</span>
              <span className="text-xl mb-1" style={{ color: "rgba(255,255,255,0.3)" }}>/10</span>
            </div>
          </div>
          <div
            className="w-20 h-20 rounded-full flex items-center justify-center text-3xl font-bold"
            style={{
              background: `conic-gradient(${scoreColor} ${score * 36}deg, rgba(255,255,255,0.06) 0deg)`,
              boxShadow: `0 0 30px ${scoreColor}30`,
            }}
          >
            <div
              className="w-14 h-14 rounded-full flex items-center justify-center text-lg font-bold"
              style={{ background: "#0a0b0f", color: scoreColor }}
            >
              {score}
            </div>
          </div>
        </div>
        <div className="score-bar-track mb-3">
          <div
            className="score-bar-fill"
            style={{ width: `${score * 10}%`, background: scoreColor }}
          />
        </div>
        {analysis.nota_geral?.justificativa && (
          <p className="text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>
            {analysis.nota_geral.justificativa}
          </p>
        )}
      </div>

      {/* Transcription */}
      {transcription && transcription !== "[Transcrição não disponível]" && (
        <div className="card p-6">
          <p className="section-title mb-3">Transcrição do Áudio</p>
          <p className="text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.75)" }}>
            {transcription}
          </p>
        </div>
      )}

      {/* Hook Visual */}
      {analysis.hook_visual && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="section-title">Hook Visual (primeiros 3s)</p>
            {analysis.hook_visual.avaliacao && (
              <span className={`badge ${getAvaliacaoBadge(analysis.hook_visual.avaliacao)}`}>
                {analysis.hook_visual.avaliacao}
              </span>
            )}
          </div>
          {analysis.hook_visual.descricao && (
            <p className="text-sm mb-3" style={{ color: "rgba(255,255,255,0.75)" }}>
              {analysis.hook_visual.descricao}
            </p>
          )}
          {analysis.hook_visual.elementos && analysis.hook_visual.elementos.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {analysis.hook_visual.elementos.map((el, i) => (
                <span key={i} className="badge badge-default">{el}</span>
              ))}
            </div>
          )}
          {analysis.hook_visual.justificativa && (
            <p className="text-xs italic" style={{ color: "rgba(255,255,255,0.4)" }}>
              {analysis.hook_visual.justificativa}
            </p>
          )}
        </div>
      )}

      {/* Formato + Presença Humana */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {analysis.formato && (
          <div className="card p-6">
            <p className="section-title mb-3">Formato</p>
            {analysis.formato.tipo && (
              <span className="badge badge-default mb-2">{analysis.formato.tipo}</span>
            )}
            {analysis.formato.descricao && (
              <p className="text-sm mt-2" style={{ color: "rgba(255,255,255,0.65)" }}>
                {analysis.formato.descricao}
              </p>
            )}
          </div>
        )}
        {analysis.presenca_humana && (
          <div className="card p-6">
            <p className="section-title mb-3">Presença Humana</p>
            <div className="flex items-center gap-2 mb-2">
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: analysis.presenca_humana.tem_rosto ? "#22c55e" : "#ef4444" }}
              />
              <span className="text-sm font-semibold">
                {analysis.presenca_humana.tem_rosto ? "Tem rosto" : "Sem rosto"}
              </span>
            </div>
            {analysis.presenca_humana.tipo && (
              <span className="badge badge-default mb-2">{analysis.presenca_humana.tipo}</span>
            )}
            {analysis.presenca_humana.descricao && (
              <p className="text-sm mt-2" style={{ color: "rgba(255,255,255,0.65)" }}>
                {analysis.presenca_humana.descricao}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Texto em Tela */}
      {analysis.texto_em_tela && (
        <div className="card p-6">
          <p className="section-title mb-3">Texto em Tela</p>
          {analysis.texto_em_tela.tipos && analysis.texto_em_tela.tipos.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {analysis.texto_em_tela.tipos.map((t, i) => (
                <span key={i} className="badge badge-default">{t}</span>
              ))}
            </div>
          )}
          {analysis.texto_em_tela.descricao && (
            <p className="text-sm" style={{ color: "rgba(255,255,255,0.65)" }}>
              {analysis.texto_em_tela.descricao}
            </p>
          )}
        </div>
      )}

      {/* Cores + Edição */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {analysis.cores_dominantes && (
          <div className="card p-6">
            <p className="section-title mb-3">Cores Dominantes</p>
            {analysis.cores_dominantes.cores && analysis.cores_dominantes.cores.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {analysis.cores_dominantes.cores.map((c, i) => (
                  <span key={i} className="badge badge-default">{c}</span>
                ))}
              </div>
            )}
            {analysis.cores_dominantes.estilo_visual && (
              <p className="text-sm" style={{ color: "rgba(255,255,255,0.65)" }}>
                {analysis.cores_dominantes.estilo_visual}
              </p>
            )}
          </div>
        )}
        {analysis.edicao && (
          <div className="card p-6">
            <p className="section-title mb-3">Edição</p>
            <div className="flex flex-wrap gap-2 mb-3">
              {analysis.edicao.ritmo && (
                <span className="badge badge-default">{analysis.edicao.ritmo}</span>
              )}
              {analysis.edicao.cortes_por_minuto_estimado && (
                <span className="badge badge-default font-mono">
                  ~{analysis.edicao.cortes_por_minuto_estimado} cortes/min
                </span>
              )}
            </div>
            {analysis.edicao.transicoes && (
              <p className="text-xs mb-2" style={{ color: "rgba(255,255,255,0.45)" }}>
                Transições: {analysis.edicao.transicoes}
              </p>
            )}
            {analysis.edicao.descricao && (
              <p className="text-sm" style={{ color: "rgba(255,255,255,0.65)" }}>
                {analysis.edicao.descricao}
              </p>
            )}
          </div>
        )}
      </div>

      {/* CTA Visual */}
      {analysis.cta_visual && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-3">
            <p className="section-title">CTA Visual</p>
            <span
              className="badge"
              style={{
                background: analysis.cta_visual.tem_cta ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
                color: analysis.cta_visual.tem_cta ? "#22c55e" : "#ef4444",
                border: `1px solid ${analysis.cta_visual.tem_cta ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
              }}
            >
              {analysis.cta_visual.tem_cta ? "Tem CTA" : "Sem CTA"}
            </span>
          </div>
          {analysis.cta_visual.tipo && (
            <span className="badge badge-default mb-2">{analysis.cta_visual.tipo}</span>
          )}
          {analysis.cta_visual.descricao && (
            <p className="text-sm mt-2" style={{ color: "rgba(255,255,255,0.65)" }}>
              {analysis.cta_visual.descricao}
            </p>
          )}
        </div>
      )}

      {/* Pontos Fortes / Fracos / Sugestões */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {analysis.pontos_fortes && analysis.pontos_fortes.length > 0 && (
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-base">✅</span>
              <p className="section-title">Pontos Fortes</p>
            </div>
            <ListItems items={analysis.pontos_fortes} color="#22c55e" />
          </div>
        )}
        {analysis.pontos_fracos && analysis.pontos_fracos.length > 0 && (
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-base">⚠️</span>
              <p className="section-title">Pontos Fracos</p>
            </div>
            <ListItems items={analysis.pontos_fracos} color="#eab308" />
          </div>
        )}
        {analysis.sugestoes && analysis.sugestoes.length > 0 && (
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-base">💡</span>
              <p className="section-title">Sugestões</p>
            </div>
            <ListItems items={analysis.sugestoes} color="#818cf8" />
          </div>
        )}
      </div>

      {/* Export */}
      <div className="flex justify-center pt-2 pb-8">
        <button
          onClick={exportReport}
          className="px-6 py-3 rounded-xl font-semibold text-white gradient-bg flex items-center gap-2 hover:opacity-90 transition-opacity"
        >
          <span>📋</span> Copiar Relatório Completo
        </button>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function Home() {
  const [mode, setMode] = useState<InputMode>("video");
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const [imagePreviewUrls, setImagePreviewUrls] = useState<string[]>([]);
  const [step, setStep] = useState<Step>("idle");
  const [currentStep, setCurrentStep] = useState(0);
  const [transcription, setTranscription] = useState("");
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");
  const [manualTranscription, setManualTranscription] = useState("");
  const [showManual, setShowManual] = useState(false);

  const handleVideoFiles = (files: File[]) => {
    const f = files[0];
    if (!f) return;
    setVideoFile(f);
    setVideoPreviewUrl(URL.createObjectURL(f));
    setStep("idle");
    setAnalysis(null);
    setError("");
  };

  const handleImageFiles = (files: File[]) => {
    setImageFiles(files);
    setImagePreviewUrls(files.map((f) => URL.createObjectURL(f)));
    setStep("idle");
    setAnalysis(null);
    setError("");
  };

  const steps = mode === "video"
    ? ["Enviando vídeo...", "Transcrevendo áudio...", "Analisando criativo..."]
    : ["Enviando imagens...", "Analisando criativo..."];

  const analyze = async () => {
    setError("");
    setAnalysis(null);
    setStep("uploading");
    setCurrentStep(0);

    try {
      if (mode === "video") {
        if (!videoFile) return;

        const fd = new FormData();
        fd.append("video", videoFile);

        setCurrentStep(0);
        const res = await fetch("/api/analyze", { method: "POST", body: fd });

        setCurrentStep(1);
        await new Promise((r) => setTimeout(r, 300));
        setCurrentStep(2);

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Erro ao analisar");

        setTranscription(data.transcription || "");
        setAnalysis(data.analysis);
      } else {
        if (imageFiles.length === 0) return;

        const fd = new FormData();
        imageFiles.forEach((f) => fd.append("images", f));

        setCurrentStep(0);
        const res = await fetch("/api/analyze-images", { method: "POST", body: fd });

        setCurrentStep(1);
        await new Promise((r) => setTimeout(r, 300));

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Erro ao analisar");

        setAnalysis(data.analysis);
      }

      setStep("done");
      setCurrentStep(steps.length);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro desconhecido";
      setError(msg);
      setStep("error");
    }
  };

  const reset = () => {
    setVideoFile(null);
    setImageFiles([]);
    setVideoPreviewUrl(null);
    setImagePreviewUrls([]);
    setStep("idle");
    setAnalysis(null);
    setError("");
    setTranscription("");
    setManualTranscription("");
    setShowManual(false);
  };

  const isProcessing = step === "uploading" || step === "transcribing" || step === "analyzing";
  const hasFile = mode === "video" ? !!videoFile : imageFiles.length > 0;

  return (
    <div style={{ background: "#0a0b0f", minHeight: "100vh" }}>
      {/* Header */}
      <header
        style={{
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          background: "rgba(255,255,255,0.02)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 50,
        }}
      >
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center text-lg"
              style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}
            >
              🔍
            </div>
            <div>
              <span className="font-bold text-white text-lg tracking-tight">Alpha Media</span>
              <span
                className="ml-2 text-xs font-mono"
                style={{ color: "rgba(255,255,255,0.35)" }}
              >
                Analisador de Criativos
              </span>
            </div>
          </div>
          {analysis && (
            <button
              onClick={reset}
              className="text-sm px-4 py-1.5 rounded-lg"
              style={{
                border: "1px solid rgba(255,255,255,0.1)",
                color: "rgba(255,255,255,0.6)",
              }}
            >
              Nova análise
            </button>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        {/* Upload Screen */}
        {!analysis && (
          <div className="animate-slide-up">
            {/* Hero */}
            <div className="text-center mb-10">
              <h1 className="text-4xl font-bold text-white mb-3">
                Analise seu{" "}
                <span className="gradient-text">criativo de anúncio</span>
              </h1>
              <p style={{ color: "rgba(255,255,255,0.45)" }} className="text-lg">
                IA especializada em direct response para o mercado brasileiro
              </p>
            </div>

            {/* Mode Tabs */}
            <div
              className="flex gap-1 p-1 rounded-xl mb-6 mx-auto"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.07)",
                width: "fit-content",
              }}
            >
              {(["video", "images"] as InputMode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => { setMode(m); reset(); }}
                  className="px-5 py-2 rounded-lg text-sm font-semibold transition-all"
                  style={
                    mode === m
                      ? { background: "linear-gradient(135deg,#6366f1,#8b5cf6)", color: "#fff" }
                      : { color: "rgba(255,255,255,0.45)" }
                  }
                >
                  {m === "video" ? "🎬 Vídeo" : "🖼️ Screenshots"}
                </button>
              ))}
            </div>

            {/* Drop Zones */}
            <div className="grid grid-cols-1 gap-4 mb-6">
              <DropZone mode={mode} onFiles={mode === "video" ? handleVideoFiles : handleImageFiles} disabled={isProcessing} />
            </div>

            {/* Preview */}
            {mode === "video" && videoPreviewUrl && (
              <div className="card p-4 mb-6">
                <p className="section-title mb-3">Preview</p>
                <video
                  src={videoPreviewUrl}
                  controls
                  className="w-full rounded-lg"
                  style={{ maxHeight: 300 }}
                />
                <p className="text-xs mt-2" style={{ color: "rgba(255,255,255,0.35)" }}>
                  {videoFile?.name} — {((videoFile?.size || 0) / 1024 / 1024).toFixed(1)} MB
                </p>
              </div>
            )}
            {mode === "images" && imagePreviewUrls.length > 0 && (
              <div className="card p-4 mb-6">
                <p className="section-title mb-3">
                  {imagePreviewUrls.length} imagem(ns) selecionada(s)
                </p>
                <div className="flex gap-3 flex-wrap">
                  {imagePreviewUrls.map((url, i) => (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      key={i}
                      src={url}
                      alt={`preview ${i}`}
                      className="rounded-lg object-cover"
                      style={{ width: 100, height: 80 }}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Manual transcription (collapsible, video only) */}
            {mode === "video" && videoFile && (
              <div className="mb-6">
                <button
                  onClick={() => setShowManual(!showManual)}
                  className="text-sm flex items-center gap-1"
                  style={{ color: "rgba(255,255,255,0.4)" }}
                >
                  <span>{showManual ? "▼" : "▶"}</span> Colar transcrição manual (opcional)
                </button>
                {showManual && (
                  <textarea
                    className="w-full mt-2 p-3 rounded-lg text-sm"
                    style={{
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(255,255,255,0.1)",
                      color: "#e2e8f0",
                      resize: "vertical",
                      minHeight: 80,
                    }}
                    placeholder="Cole a transcrição aqui se o Whisper falhar..."
                    value={manualTranscription}
                    onChange={(e) => setManualTranscription(e.target.value)}
                  />
                )}
              </div>
            )}

            {/* Progress Steps (while processing) */}
            {isProcessing && (
              <div className="card p-6 mb-6 animate-fade-in">
                <p className="section-title mb-4">Processando...</p>
                <div className="space-y-2">
                  {steps.map((label, i) => {
                    const state =
                      currentStep > i ? "done" : currentStep === i ? "active" : "pending";
                    return (
                      <div key={i} className={`step-item ${state}`}>
                        <StepIcon state={state} />
                        <span
                          className="text-sm"
                          style={{ color: state === "pending" ? "rgba(255,255,255,0.35)" : "#e2e8f0" }}
                        >
                          {label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div
                className="card p-4 mb-6 animate-fade-in"
                style={{ border: "1px solid rgba(239,68,68,0.3)", background: "rgba(239,68,68,0.05)" }}
              >
                <p className="text-sm font-semibold mb-1" style={{ color: "#ef4444" }}>
                  Erro na análise
                </p>
                <p className="text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>{error}</p>
              </div>
            )}

            {/* Analyze Button */}
            <div className="flex justify-center">
              <button
                onClick={analyze}
                disabled={!hasFile || isProcessing}
                className="px-8 py-4 rounded-xl font-bold text-white text-base transition-all animate-pulse-glow"
                style={{
                  background:
                    !hasFile || isProcessing
                      ? "rgba(99,102,241,0.3)"
                      : "linear-gradient(135deg,#6366f1,#8b5cf6)",
                  cursor: !hasFile || isProcessing ? "not-allowed" : "pointer",
                  minWidth: 220,
                }}
              >
                {isProcessing ? "Analisando..." : "Analisar Criativo"}
              </button>
            </div>
          </div>
        )}

        {/* Results Screen */}
        {analysis && (
          <div>
            <div className="flex items-center gap-4 mb-8">
              <div>
                <h2 className="text-2xl font-bold text-white">Relatório de Análise</h2>
                <p className="text-sm" style={{ color: "rgba(255,255,255,0.4)" }}>
                  {mode === "video" ? videoFile?.name : `${imageFiles.length} imagem(ns)`}
                </p>
              </div>
            </div>
            <ResultsView analysis={analysis} transcription={transcription || manualTranscription} />
          </div>
        )}
      </main>
    </div>
  );
}
