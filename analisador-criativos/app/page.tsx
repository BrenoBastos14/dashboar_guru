"use client";

import React, { useState, useRef, useCallback, useEffect, DragEvent, ChangeEvent } from "react";

interface FeedbackEntry {
  id: string;
  date: string;
  videoName: string;
  notaGemini: number;
  formato: string;
  resultado: string;
  gasto: string;
  roas: string;
  observacoes: string;
  hookAvaliacao: string;
  ctaAvaliacao: string;
}

// ─── Types ───────────────────────────────────────────────────────────────────

interface ScoreEntry { nota: number; label: string; obs: string; }

interface SubPersona {
  descricao?: string; medo_dominante?: string; desejo_dominante?: string; objecao_principal?: string;
  como_adaptaria_hook?: string; como_adaptaria_medo?: string;
}

interface InvalidacaoCiclo {
  solucoes_invalidadas?: string[]; tem_reason_why?: boolean; reason_why_tipo?: string;
  conectada_ao_mup?: boolean; qualidade?: string; trecho?: string;
}

interface AnalysisResult {
  scorecard?: {
    nota_geral?: number;
    classificacao?: string;
    notas?: {
      hook?: ScoreEntry; qualificacao?: ScoreEntry; invalidacao?: ScoreEntry;
      mup?: ScoreEntry; medo?: ScoreEntry; expert?: ScoreEntry;
      msol?: ScoreEntry; provas?: ScoreEntry; cta?: ScoreEntry;
      escassez?: ScoreEntry; linguagem?: ScoreEntry; visual?: ScoreEntry;
    };
  };
  variaveis?: {
    publico_alvo?: string;
    expert?: { identificado?: boolean; nome?: string; camadas?: number; descricao?: string };
    mup?: { identificado?: boolean; descricao?: string; qualidade?: string };
    muf?: { identificado?: boolean; descricao?: string; qualidade?: string };
    mus?: { identificado?: boolean; nome?: string; tem_nome_proprietario?: boolean; tem_tempo_curto?: boolean; tem_simplicidade?: boolean; descricao?: string };
    promessa?: { camadas_usadas?: string[]; tipo?: string; descricao?: string };
  };
  sub_personas?: {
    atual?: SubPersona;
    alternativas?: SubPersona[];
  };
  teasings?: {
    mup_teasings?: string[];
    muf_teasings?: string[];
    mus_teasings?: string[];
    nomes_chiclete?: string[];
  };
  analise_hook?: {
    angulo_identificado?: string; beneficio_tipo?: string; beneficio_camada?: string;
    forca?: string; texto_do_hook?: string; justificativa?: string;
  };
  estrutura?: {
    blocos_presentes?: { bloco: string; qualidade: string; trecho: string }[];
    blocos_ausentes?: string[];
    formato_usado?: string;
    invalidacoes?: {
      quantidade?: number;
      ciclos?: InvalidacaoCiclo[];
      invalidacoes_sugeridas?: { solucao_a_invalidar: string; reason_why: string; texto_sugerido: string }[];
    };
    provas?: { tipos_encontrados?: string[]; quantidade?: number; qualidade?: string };
    ctas?: { quantidade?: number; distribuicao?: string; destino?: string };
  };
  bullets?: {
    encontrados?: { tipo: string; texto: string; qualidade: string }[];
    tem_nomeacao_proprietaria?: boolean; tem_especificidade?: boolean;
    tem_parenteses_consequencia?: boolean; qualidade_geral?: string;
  };
  linguagem_detalhada?: {
    nivel?: string; nota_visceral?: number;
    trechos_genericos?: { original: string; reescrita_visceral: string }[];
    verbos_fracos_encontrados?: string[];
    verbos_fortes_sugeridos?: string[];
  };
  visual?: {
    formato?: string; hook_visual_descricao?: string; presenca_humana?: string;
    tipo_presenca?: string; texto_em_tela?: boolean; tipos_texto?: string[];
    ritmo_edicao?: string; cta_visual?: string;
  };
  diagnostico?: {
    pontos_fortes?: string[]; pontos_fracos?: string[];
    top3_melhorias?: { prioridade: number; acao: string; justificativa: string; impacto: string; framework: string }[];
  };
  gerador?: {
    hooks_alternativos?: { angulo: string; hook: string; beneficio_camada: string; teasing_usado?: string }[];
    bullets_sugeridos?: { tipo: string; esfera?: string; bullet: string; posicao_ideal: string; tem_nomeacao?: boolean; tem_parenteses?: boolean }[];
    mup_alternativo?: string; msol_alternativo?: string; future_pacing_sugerido?: string;
  };
  raw?: string;
}

type Step = "idle" | "uploading" | "transcribing" | "analyzing" | "done" | "error";
type InputMode = "video" | "images" | "url";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getScoreColor(score: number) {
  if (score >= 8) return "#22c55e";
  if (score >= 5) return "#eab308";
  return "#ef4444";
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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button
      onClick={copy}
      className="text-xs px-2.5 py-1 rounded-lg flex-shrink-0"
      style={{ background: copied ? "rgba(34,197,94,0.15)" : "rgba(255,255,255,0.06)", color: copied ? "#22c55e" : "rgba(255,255,255,0.5)", border: `1px solid ${copied ? "rgba(34,197,94,0.3)" : "rgba(255,255,255,0.08)"}` }}
    >
      {copied ? "✓ Copiado" : "Copiar"}
    </button>
  );
}

function CollapsibleSection({ title, emoji, children, defaultOpen = false }: { title: string; emoji: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-5 py-4"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-2">
          <span>{emoji}</span>
          <span className="font-semibold text-white text-sm">{title}</span>
        </div>
        <span style={{ color: "rgba(255,255,255,0.4)", fontSize: 12 }}>{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  );
}

// ─── Rewrite Block Modal ─────────────────────────────────────────────────────

function RewriteBlockModal({ bloco, trecho, nota, variaveis, onClose }: {
  bloco: string; trecho: string; nota: number; variaveis: AnalysisResult["variaveis"]; onClose: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [versoes, setVersoes] = useState<{ versao: number; texto: string; nota_estimada: number; o_que_mudou: string }[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    fetch("/api/rewrite-block", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bloco, trecho, nota, obs: "", variaveis: variaveis || {} }),
    })
      .then(r => r.json())
      .then(data => { setVersoes(data.versoes || []); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [bloco, trecho, nota, variaveis]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-10 px-4 pb-10" style={{ background: "rgba(0,0,0,0.8)", backdropFilter: "blur(8px)", overflowY: "auto" }} onClick={onClose}>
      <div className="w-full max-w-lg card p-6 animate-slide-up" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-bold text-white">✏️ Reescrever Bloco</h2>
            <p className="text-xs mt-0.5" style={{ color: "#818cf8" }}>{bloco}</p>
          </div>
          <button onClick={onClose} className="text-sm px-3 py-1 rounded-lg" style={{ border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.5)" }}>✕</button>
        </div>
        {trecho && (
          <div className="rounded-lg p-3 mb-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
            <p className="text-xs mb-1" style={{ color: "rgba(255,255,255,0.4)" }}>Trecho original</p>
            <p className="text-sm italic" style={{ color: "rgba(255,255,255,0.65)" }}>&ldquo;{trecho}&rdquo;</p>
          </div>
        )}
        {loading && <p className="text-center py-8" style={{ color: "rgba(255,255,255,0.4)" }}>Gerando versões...</p>}
        {error && <p className="text-sm py-4" style={{ color: "#ef4444" }}>{error}</p>}
        <div className="space-y-3">
          {versoes.map((v, i) => (
            <div key={i} className="rounded-xl p-4" style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.2)" }}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold" style={{ color: "#818cf8" }}>Versão {v.versao}</span>
                  {v.nota_estimada && <span className="text-xs font-mono" style={{ color: getScoreColor(v.nota_estimada) }}>{v.nota_estimada}/10</span>}
                </div>
                <CopyButton text={v.texto} />
              </div>
              <p className="text-sm" style={{ color: "#e2e8f0", lineHeight: 1.6 }}>{v.texto}</p>
              {v.o_que_mudou && <p className="text-xs mt-2 italic" style={{ color: "rgba(255,255,255,0.4)" }}>{v.o_que_mudou}</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Remessa Modal ───────────────────────────────────────────────────────────

function RemessaModal({ analysis, onClose }: { analysis: AnalysisResult; onClose: () => void }) {
  const [loading, setLoading] = useState(false);
  const [remessa, setRemessa] = useState<{ titulo: string; abertura_1: string; abertura_2: string; corpo: string; cta: string; badge?: string }[]>([]);
  const [logica, setLogica] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    fetch("/api/generate-remessa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis }),
    })
      .then(r => r.json())
      .then(data => { setRemessa(data.remessa || []); setLogica(data.logica_da_remessa || ""); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [analysis]);

  const allText = remessa.map((r, i) => `--- Ad ${i+1}: ${r.titulo} ---\nAbertura A: ${r.abertura_1}\nAbertura B: ${r.abertura_2}\nCorpo: ${r.corpo}\nCTA: ${r.cta}`).join("\n\n");

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-8 px-4 pb-10" style={{ background: "rgba(0,0,0,0.8)", backdropFilter: "blur(8px)", overflowY: "auto" }} onClick={onClose}>
      <div className="w-full max-w-3xl card p-6 animate-slide-up" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="font-bold text-white text-lg">📦 Remessa Coringa</h2>
            <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>6 variações de anúncio com 2 aberturas cada</p>
          </div>
          <div className="flex items-center gap-2">
            {remessa.length > 0 && <CopyButton text={allText} />}
            <button onClick={onClose} className="text-sm px-3 py-1 rounded-lg" style={{ border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.5)" }}>✕</button>
          </div>
        </div>
        {loading && <p className="text-center py-12" style={{ color: "rgba(255,255,255,0.4)" }}>Gerando remessa...</p>}
        {error && <p className="text-sm py-4" style={{ color: "#ef4444" }}>{error}</p>}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {remessa.map((r, i) => (
            <div key={i} className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.15)", color: "#818cf8" }}>Ad {i+1}</span>
                  {r.badge && <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: r.badge === "Validado" ? "rgba(34,197,94,0.15)" : "rgba(234,179,8,0.15)", color: r.badge === "Validado" ? "#4ade80" : "#eab308" }}>{r.badge}</span>}
                </div>
                <CopyButton text={`${r.abertura_1}\n\n${r.corpo}\n\n${r.cta}`} />
              </div>
              <p className="text-sm font-bold text-white mb-3">{r.titulo}</p>
              <div className="space-y-2">
                <div className="rounded p-2" style={{ background: "rgba(99,102,241,0.06)" }}>
                  <p className="text-xs mb-0.5" style={{ color: "#818cf8" }}>Abertura A</p>
                  <p className="text-xs" style={{ color: "rgba(255,255,255,0.75)" }}>{r.abertura_1}</p>
                </div>
                <div className="rounded p-2" style={{ background: "rgba(139,92,246,0.06)" }}>
                  <p className="text-xs mb-0.5" style={{ color: "#a78bfa" }}>Abertura B</p>
                  <p className="text-xs" style={{ color: "rgba(255,255,255,0.75)" }}>{r.abertura_2}</p>
                </div>
                <p className="text-xs" style={{ color: "rgba(255,255,255,0.6)", lineHeight: 1.5 }}>{r.corpo}</p>
                <p className="text-xs font-semibold" style={{ color: "#22c55e" }}>{r.cta}</p>
              </div>
            </div>
          ))}
        </div>
        {logica && !loading && (
          <div className="mt-4 rounded-xl p-4" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <p className="text-xs font-bold mb-1" style={{ color: "rgba(255,255,255,0.4)" }}>Lógica da remessa</p>
            <p className="text-xs" style={{ color: "rgba(255,255,255,0.5)", lineHeight: 1.6 }}>{logica}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Tournament Modal ───────────────────────────────────────────────────────

type TournamentTipo = "hook" | "body" | "cta";

interface TournamentRound {
  round: number;
  versions: { A: string; B: string; AB: string };
  scores: { A: number; B: number; AB: number };
  winner: "A" | "B" | "AB";
  motivos: string[];
}

interface TournamentResult {
  tipo: TournamentTipo;
  initial_text: string;
  final_text: string;
  rounds: TournamentRound[];
  converged: boolean;
  total_rounds: number;
}

function TournamentModal({ tipo, initialText, analysis, onClose }: {
  tipo: TournamentTipo;
  initialText: string;
  analysis: AnalysisResult;
  onClose: () => void;
}) {
  const [currentText, setCurrentText] = useState(initialText);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TournamentResult | null>(null);
  const [error, setError] = useState("");
  const [phase, setPhase] = useState("");

  const runTournament = async () => {
    if (!currentText.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    setPhase("⚔️ Iniciando torneio...");
    try {
      const res = await fetch("/api/tournament", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tipo, current_text: currentText, analysis }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erro no torneio");
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro desconhecido");
    } finally {
      setLoading(false);
      setPhase("");
    }
  };

  const titulo = tipo === "hook" ? "Hook" : tipo === "body" ? "Body" : "CTA";
  const cor = tipo === "hook" ? "#f472b6" : tipo === "body" ? "#818cf8" : "#22c55e";
  const bgCor = tipo === "hook" ? "rgba(236,72,153,0.1)" : tipo === "body" ? "rgba(99,102,241,0.1)" : "rgba(34,197,94,0.1)";

  const versionLabels: Record<"A" | "B" | "AB", string> = {
    A: "Original (A)",
    B: "Adversarial (B)",
    AB: "Síntese (A+B)",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-8 px-4 pb-10" style={{ background: "rgba(0,0,0,0.82)", backdropFilter: "blur(8px)", overflowY: "auto" }} onClick={onClose}>
      <div className="w-full max-w-2xl card p-6 animate-slide-up" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="font-bold text-white text-lg">⚔️ Torneio de {titulo}</h2>
            <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.45)" }}>
              Autoreason · 3 versões × 3 juízes cegos · Borda counting
            </p>
          </div>
          <button onClick={onClose} className="text-sm px-3 py-1 rounded-lg" style={{ border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.5)" }}>✕</button>
        </div>

        {!result && (
          <>
            <div className="mb-4">
              <p className="section-title mb-1">Texto inicial do {titulo.toLowerCase()}</p>
              <textarea
                value={currentText}
                onChange={(e) => setCurrentText(e.target.value)}
                rows={tipo === "body" ? 6 : 3}
                disabled={loading}
                className="w-full px-3 py-2 rounded-lg text-sm resize-none"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.12)", color: "#e2e8f0", lineHeight: 1.6 }}
              />
              <p className="text-xs mt-1" style={{ color: "rgba(255,255,255,0.35)" }}>Edite se necessário antes de rodar o torneio.</p>
            </div>

            <button
              onClick={runTournament}
              disabled={loading || !currentText.trim()}
              className="w-full py-3 rounded-xl font-bold text-white transition-all"
              style={{ background: loading ? "rgba(99,102,241,0.3)" : "linear-gradient(135deg,#6366f1,#8b5cf6)", cursor: loading ? "not-allowed" : "pointer" }}
            >
              {loading ? (phase || "Processando torneio (até ~60s)...") : `⚔️ Iniciar Torneio de ${titulo}`}
            </button>

            <div className="mt-4 rounded-lg p-3 text-xs" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.55)", lineHeight: 1.6 }}>
              <p className="font-semibold mb-1" style={{ color: "rgba(255,255,255,0.75)" }}>Como funciona:</p>
              <p>• <b style={{ color: cor }}>A</b>: texto atual · <b style={{ color: cor }}>B</b>: crítico adversarial reescreve atacando fraquezas · <b style={{ color: cor }}>AB</b>: sintetizador combina forças de A+B</p>
              <p>• 3 juízes independentes ranqueiam cegamente (não sabem qual é qual)</p>
              <p>• Borda count: 3pts p/ 1º, 2pts p/ 2º, 1pt p/ 3º</p>
              <p>• Converge quando o mesmo vencedor ganha 2 rounds seguidos (máx 3 rounds)</p>
            </div>
          </>
        )}

        {error && (
          <div className="mt-3 rounded-xl p-3" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)" }}>
            <p className="text-sm" style={{ color: "#ef4444" }}>{error}</p>
          </div>
        )}

        {result && (
          <div className="space-y-4">
            {/* Vencedor */}
            <div className="rounded-xl p-5" style={{ background: bgCor, border: `1px solid ${cor}40` }}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: cor + "25", color: cor }}>🏆 Vencedor</span>
                  <span className="text-xs" style={{ color: "rgba(255,255,255,0.5)" }}>
                    {result.total_rounds} round{result.total_rounds > 1 ? "s" : ""} · {result.converged ? "Convergiu" : "Limite atingido"}
                  </span>
                </div>
                <CopyButton text={result.final_text} />
              </div>
              <p className="text-sm" style={{ color: "#e2e8f0", lineHeight: 1.6 }}>{result.final_text}</p>
            </div>

            {/* Comparação com original */}
            {result.initial_text !== result.final_text && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="rounded-lg p-3" style={{ background: "rgba(239,68,68,0.04)", border: "1px solid rgba(239,68,68,0.15)" }}>
                  <p className="text-xs mb-1" style={{ color: "#ef4444" }}>Antes</p>
                  <p className="text-xs" style={{ color: "rgba(255,255,255,0.55)", lineHeight: 1.5 }}>{result.initial_text}</p>
                </div>
                <div className="rounded-lg p-3" style={{ background: "rgba(34,197,94,0.04)", border: "1px solid rgba(34,197,94,0.15)" }}>
                  <p className="text-xs mb-1" style={{ color: "#22c55e" }}>Depois</p>
                  <p className="text-xs" style={{ color: "rgba(255,255,255,0.75)", lineHeight: 1.5 }}>{result.final_text}</p>
                </div>
              </div>
            )}

            {/* Rounds */}
            <div>
              <p className="section-title mb-2">📜 Histórico do torneio</p>
              <div className="space-y-3">
                {result.rounds.map((r) => (
                  <div key={r.round} className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-xs font-bold text-white">Round {r.round}</p>
                      <div className="flex items-center gap-2 flex-wrap justify-end">
                        {(["A", "B", "AB"] as const).map((id) => (
                          <span key={id} className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: r.winner === id ? cor + "25" : "rgba(255,255,255,0.04)", color: r.winner === id ? cor : "rgba(255,255,255,0.5)", border: r.winner === id ? `1px solid ${cor}50` : "1px solid rgba(255,255,255,0.08)" }}>
                            {id}: {r.scores[id]}pts{r.winner === id ? " 🏆" : ""}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="space-y-2">
                      {(["A", "B", "AB"] as const).map((id) => (
                        <div key={id} className="rounded p-2" style={{ background: r.winner === id ? cor + "08" : "rgba(255,255,255,0.02)", border: `1px solid ${r.winner === id ? cor + "30" : "rgba(255,255,255,0.05)"}` }}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-bold" style={{ color: r.winner === id ? cor : "rgba(255,255,255,0.5)" }}>{versionLabels[id]}</span>
                            <CopyButton text={r.versions[id]} />
                          </div>
                          <p className="text-xs" style={{ color: "rgba(255,255,255,0.7)", lineHeight: 1.5 }}>{r.versions[id]}</p>
                        </div>
                      ))}
                    </div>
                    {r.motivos.length > 0 && (
                      <div className="mt-2 pt-2" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                        {r.motivos.map((m, i) => (
                          <p key={i} className="text-xs italic" style={{ color: "rgba(255,255,255,0.4)" }}>Juiz {i + 1}: {m}</p>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => { setResult(null); setCurrentText(result.final_text); }}
              className="w-full py-2.5 rounded-xl text-sm font-semibold"
              style={{ border: `1px solid ${cor}30`, color: cor, background: "transparent" }}
            >
              ↺ Rodar novo torneio usando o vencedor como base
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function ResultsView({ analysis, transcription }: { analysis: AnalysisResult; transcription?: string }) {
  const [rewriteTarget, setRewriteTarget] = useState<{ bloco: string; trecho: string; nota: number } | null>(null);
  const [tournamentTipo, setTournamentTipo] = useState<TournamentTipo | null>(null);
  // Compute nota_geral client-side as fallback for weighted average
  const notas = analysis.scorecard?.notas;
  const computedScore = notas
    ? (() => {
        const h = notas.hook?.nota ?? 0;
        const mup = notas.mup?.nota ?? 0;
        const msol = notas.msol?.nota ?? 0;
        const provas = notas.provas?.nota ?? 0;
        const rest = [notas.qualificacao, notas.invalidacao, notas.medo, notas.expert, notas.cta, notas.escassez, notas.linguagem, notas.visual]
          .reduce((s, e) => s + (e?.nota ?? 0), 0);
        const total = h * 2 + mup * 1.5 + msol * 1.5 + provas * 1.2 + rest;
        const weights = 2 + 1.5 + 1.5 + 1.2 + 8;
        return Math.round((total / weights) * 10) / 10;
      })()
    : 0;
  const score = analysis.scorecard?.nota_geral ?? computedScore;
  const scoreColor = getScoreColor(score);
  const classificacao = analysis.scorecard?.classificacao || "";

  const scoreRows = notas
    ? [
        notas.hook, notas.qualificacao, notas.invalidacao, notas.mup,
        notas.medo, notas.expert, notas.msol, notas.provas,
        notas.cta, notas.escassez, notas.linguagem, notas.visual,
      ].filter(Boolean) as ScoreEntry[]
    : [];

  // Helpers para extrair texto inicial de cada seção
  const initialHook = analysis.analise_hook?.texto_do_hook ||
    analysis.estrutura?.blocos_presentes?.find((b) => b.bloco.toLowerCase().includes("hook"))?.trecho ||
    (transcription ? transcription.split(/[.!?]/).slice(0, 2).join(". ").trim() + "." : "");
  const ctaBlocos = (analysis.estrutura?.blocos_presentes || []).filter(
    (b) => /cta|escassez|future/i.test(b.bloco)
  );
  const initialCta = ctaBlocos.map((b) => b.trecho).filter(Boolean).join(" ") || "";
  const bodyBlocos = (analysis.estrutura?.blocos_presentes || []).filter(
    (b) => !/hook|cta|escassez|future/i.test(b.bloco)
  );
  const initialBody = bodyBlocos.map((b) => b.trecho).filter(Boolean).join(" ") ||
    (transcription ? transcription.slice(transcription.indexOf(".") + 1).trim() : "");

  return (
    <div className="animate-fade-in space-y-4">
      {rewriteTarget && (
        <RewriteBlockModal
          bloco={rewriteTarget.bloco}
          trecho={rewriteTarget.trecho}
          nota={rewriteTarget.nota}
          variaveis={analysis.variaveis}
          onClose={() => setRewriteTarget(null)}
        />
      )}
      {tournamentTipo && (
        <TournamentModal
          tipo={tournamentTipo}
          initialText={tournamentTipo === "hook" ? initialHook : tournamentTipo === "cta" ? initialCta : initialBody}
          analysis={analysis}
          onClose={() => setTournamentTipo(null)}
        />
      )}

      {/* ── TORNEIOS (Autoreason) ── */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="section-title">⚔️ Refinar via Torneio</p>
            <p className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
              Gera 3 versões, avalia com 3 juízes cegos e converge no vencedor (Autoreason)
            </p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {([
            { tipo: "hook", label: "Hook", emoji: "🎣", color: "#f472b6", bg: "rgba(236,72,153,0.08)", border: "rgba(236,72,153,0.25)" },
            { tipo: "body", label: "Body", emoji: "📝", color: "#818cf8", bg: "rgba(99,102,241,0.08)", border: "rgba(99,102,241,0.25)" },
            { tipo: "cta", label: "CTA", emoji: "🎯", color: "#22c55e", bg: "rgba(34,197,94,0.08)", border: "rgba(34,197,94,0.25)" },
          ] as const).map(({ tipo, label, emoji, color, bg, border }) => (
            <button
              key={tipo}
              onClick={() => setTournamentTipo(tipo)}
              className="py-3 px-4 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2"
              style={{ background: bg, border: `1px solid ${border}`, color }}
            >
              <span>{emoji}</span>
              <span>Torneio do {label}</span>
            </button>
          ))}
        </div>
      </div>


      {/* ── SCORECARD ── */}
      <div className="card p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <p className="section-title mb-1">Nota Geral</p>
            <div className="flex items-end gap-2">
              <span className="text-5xl font-bold" style={{ color: scoreColor }}>{score}</span>
              <span className="text-xl mb-1" style={{ color: "rgba(255,255,255,0.3)" }}>/10</span>
            </div>
          </div>
          <div className="text-right">
            {classificacao && (
              <span
                className="inline-block px-3 py-1 rounded-full text-sm font-bold mb-1"
                style={{ background: `${scoreColor}20`, color: scoreColor, border: `1px solid ${scoreColor}40` }}
              >
                {classificacao}
              </span>
            )}
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center font-bold text-lg"
              style={{
                background: `conic-gradient(${scoreColor} ${score * 36}deg, rgba(255,255,255,0.06) 0deg)`,
                boxShadow: `0 0 24px ${scoreColor}30`,
              }}
            >
              <div className="w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold" style={{ background: "#0a0b0f", color: scoreColor }}>
                {score}
              </div>
            </div>
          </div>
        </div>

        {/* Score bars */}
        {scoreRows.length > 0 && (
          <div className="space-y-2 mb-5">
            {scoreRows.map((row, i) => {
              const c = getScoreColor(row.nota);
              return (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs w-32 flex-shrink-0" style={{ color: "rgba(255,255,255,0.55)" }}>{row.label}</span>
                  <div className="flex-1 h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.07)" }}>
                    <div className="h-1.5 rounded-full transition-all" style={{ width: `${row.nota * 10}%`, background: c }} />
                  </div>
                  <span className="text-xs font-mono w-6 text-right" style={{ color: c }}>{row.nota}</span>
                  <span className="text-xs flex-1 hidden md:block truncate" style={{ color: "rgba(255,255,255,0.35)" }}>{row.obs}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Top 3 melhorias */}
        {analysis.diagnostico?.top3_melhorias && analysis.diagnostico.top3_melhorias.length > 0 && (
          <div>
            <p className="section-title mb-2">Top 3 Melhorias Prioritárias</p>
            <div className="space-y-2">
              {analysis.diagnostico.top3_melhorias.map((m, i) => (
                <div key={i} className="flex gap-3 items-start rounded-lg p-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                  <span
                    className="text-xs font-bold px-2 py-0.5 rounded flex-shrink-0 mt-0.5"
                    style={{ background: m.impacto === "Alto" ? "rgba(239,68,68,0.15)" : "rgba(234,179,8,0.15)", color: m.impacto === "Alto" ? "#ef4444" : "#eab308" }}
                  >
                    {m.impacto}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-white">{m.acao}</p>
                    <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.45)" }}>{m.justificativa}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── TRANSCRIÇÃO ── */}
      {transcription && transcription !== "[Transcrição não disponível]" && (
        <CollapsibleSection title="Transcrição do Áudio" emoji="🎙️" defaultOpen={false}>
          <p className="text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.75)" }}>{transcription}</p>
        </CollapsibleSection>
      )}

      {/* ── VARIÁVEIS ── */}
      {analysis.variaveis && (
        <CollapsibleSection title="Variáveis Identificadas" emoji="🔬" defaultOpen={false}>
          <div className="space-y-3">
            {[
              { label: "Público-alvo", value: analysis.variaveis.publico_alvo, icon: "👤" },
              { label: "Expert", value: analysis.variaveis.expert?.descricao ? `${analysis.variaveis.expert.nome || ""} — ${analysis.variaveis.expert.camadas || 0} camadas — ${analysis.variaveis.expert.descricao}` : null, icon: "🏅", quality: analysis.variaveis.expert?.identificado ? "Forte" : "Ausente" },
              { label: "MUP", value: analysis.variaveis.mup?.descricao, icon: "🧬", quality: analysis.variaveis.mup?.qualidade },
              { label: "MUF", value: analysis.variaveis.muf?.descricao, icon: "⚙️", quality: analysis.variaveis.muf?.qualidade },
              { label: "MSOL", value: analysis.variaveis.mus?.descricao ? `"${analysis.variaveis.mus.nome || ""}" — ${analysis.variaveis.mus.descricao}` : null, icon: "✨", quality: analysis.variaveis.mus?.identificado ? "Forte" : "Ausente" },
              { label: "Promessa", value: analysis.variaveis.promessa?.descricao, icon: "🎯", quality: analysis.variaveis.promessa?.tipo },
            ].map(({ label, value, icon, quality }) => (
              <div key={label} className="flex gap-3 items-start">
                <span className="text-base flex-shrink-0 mt-0.5">{icon}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-bold" style={{ color: "rgba(255,255,255,0.5)" }}>{label}</span>
                    {quality && (
                      <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: (quality === "Forte" || quality === "Explícita") ? "rgba(34,197,94,0.1)" : quality === "Ausente" ? "rgba(239,68,68,0.1)" : "rgba(234,179,8,0.1)", color: (quality === "Forte" || quality === "Explícita") ? "#22c55e" : quality === "Ausente" ? "#ef4444" : "#eab308" }}>
                        {quality}
                      </span>
                    )}
                  </div>
                  <p className="text-sm" style={{ color: value ? "rgba(255,255,255,0.75)" : "rgba(255,255,255,0.25)" }}>
                    {value || "Não identificado"}
                  </p>
                </div>
              </div>
            ))}
            {analysis.variaveis.promessa?.camadas_usadas && analysis.variaveis.promessa.camadas_usadas.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-1">
                {analysis.variaveis.promessa.camadas_usadas.map((c, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 rounded-full" style={{ background: "rgba(99,102,241,0.1)", color: "#818cf8", border: "1px solid rgba(99,102,241,0.2)" }}>{c}</span>
                ))}
              </div>
            )}
          </div>

          {/* Sub-personas */}
          {analysis.sub_personas && (
            <div className="mt-4 pt-4" style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}>
              <p className="text-xs font-bold mb-3" style={{ color: "rgba(255,255,255,0.5)" }}>Sub-personas</p>
              {analysis.sub_personas.atual && (
                <div className="rounded-xl p-3 mb-3" style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)" }}>
                  <p className="text-xs font-bold mb-1" style={{ color: "#818cf8" }}>Persona Atual</p>
                  <p className="text-sm font-semibold text-white mb-2">{analysis.sub_personas.atual.descricao}</p>
                  <div className="grid grid-cols-3 gap-2">
                    {[["Medo", analysis.sub_personas.atual.medo_dominante], ["Desejo", analysis.sub_personas.atual.desejo_dominante], ["Objeção", analysis.sub_personas.atual.objecao_principal]].map(([l, v]) => v ? (
                      <div key={l}><p className="text-xs mb-0.5" style={{ color: "rgba(255,255,255,0.35)" }}>{l}</p><p className="text-xs" style={{ color: "rgba(255,255,255,0.7)" }}>{v}</p></div>
                    ) : null)}
                  </div>
                </div>
              )}
              <div className="space-y-2">
                {(analysis.sub_personas.alternativas || []).filter(a => a.descricao).map((alt, i) => (
                  <div key={i} className="rounded-xl p-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <p className="text-xs font-semibold text-white mb-1">{alt.descricao}</p>
                    <div className="grid grid-cols-2 gap-2 mb-2">
                      {[["Medo", alt.medo_dominante], ["Desejo", alt.desejo_dominante]].map(([l, v]) => v ? (
                        <div key={l}><p className="text-xs mb-0.5" style={{ color: "rgba(255,255,255,0.35)" }}>{l}</p><p className="text-xs" style={{ color: "rgba(255,255,255,0.65)" }}>{v}</p></div>
                      ) : null)}
                    </div>
                    {alt.como_adaptaria_hook && <p className="text-xs italic" style={{ color: "rgba(255,255,255,0.45)" }}>Hook: {alt.como_adaptaria_hook}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CollapsibleSection>
      )}

      {/* ── TEASINGS MINERADOS ── */}
      {analysis.teasings && (
        <CollapsibleSection title="Teasings Minerados" emoji="⛏️" defaultOpen={false}>
          <div className="space-y-4">
            {[
              { label: "MUP", items: analysis.teasings.mup_teasings, color: "#ef4444", bg: "rgba(239,68,68,0.06)" },
              { label: "MUF", items: analysis.teasings.muf_teasings, color: "#eab308", bg: "rgba(234,179,8,0.06)" },
              { label: "MUS", items: analysis.teasings.mus_teasings, color: "#22c55e", bg: "rgba(34,197,94,0.06)" },
            ].map(({ label, items, color, bg }) => items && items.length > 0 && (
              <div key={label}>
                <p className="text-xs font-bold mb-2" style={{ color }}>{label} Teasings</p>
                <div className="space-y-2">
                  {items.filter(Boolean).map((t, i) => (
                    <div key={i} className="flex items-center justify-between rounded-lg p-3" style={{ background: bg, border: `1px solid ${color}20` }}>
                      <p className="text-sm flex-1 mr-3" style={{ color: "rgba(255,255,255,0.8)" }}>{t}</p>
                      <CopyButton text={t} />
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {analysis.teasings.nomes_chiclete && analysis.teasings.nomes_chiclete.length > 0 && (
              <div>
                <p className="text-xs font-bold mb-2" style={{ color: "#a78bfa" }}>Nomes Chiclete</p>
                <div className="flex flex-wrap gap-2">
                  {analysis.teasings.nomes_chiclete.filter(Boolean).map((n, i) => (
                    <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-full" style={{ background: "rgba(139,92,246,0.12)", border: "1px solid rgba(139,92,246,0.3)" }}>
                      <span className="text-sm font-bold" style={{ color: "#c4b5fd" }}>&ldquo;{n}&rdquo;</span>
                      <CopyButton text={n} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* ── ANÁLISE DO HOOK ── */}
      {analysis.analise_hook && (
        <CollapsibleSection title="Análise do Hook" emoji="🪝" defaultOpen={true}>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Ângulo", value: analysis.analise_hook.angulo_identificado },
                { label: "Força", value: analysis.analise_hook.forca },
                { label: "Benefício", value: analysis.analise_hook.beneficio_tipo },
                { label: "Camada", value: analysis.analise_hook.beneficio_camada },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-lg p-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                  <p className="text-xs mb-1" style={{ color: "rgba(255,255,255,0.4)" }}>{label}</p>
                  <p className="text-sm font-semibold text-white">{value || "—"}</p>
                </div>
              ))}
            </div>
            {analysis.analise_hook.texto_do_hook && (
              <div className="rounded-lg p-3" style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.2)" }}>
                <p className="text-xs mb-1" style={{ color: "#818cf8" }}>Texto do Hook</p>
                <p className="text-sm italic" style={{ color: "rgba(255,255,255,0.8)" }}>&ldquo;{analysis.analise_hook.texto_do_hook}&rdquo;</p>
              </div>
            )}
            {analysis.analise_hook.justificativa && (
              <p className="text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>{analysis.analise_hook.justificativa}</p>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* ── ESTRUTURA 12 BLOCOS ── */}
      {analysis.estrutura && (
        <CollapsibleSection title="Estrutura — 12 Blocos" emoji="🏗️" defaultOpen={false}>
          <div className="space-y-4">
            <div className="flex flex-wrap gap-1.5 mb-3">
              <span className="text-xs font-semibold" style={{ color: "rgba(255,255,255,0.4)" }}>Formato: </span>
              <span className="text-xs" style={{ color: "#818cf8" }}>{analysis.estrutura.formato_usado}</span>
            </div>
            {analysis.estrutura.blocos_presentes && analysis.estrutura.blocos_presentes.length > 0 && (
              <div>
                <p className="text-xs font-bold mb-2" style={{ color: "#22c55e" }}>Blocos Presentes ({analysis.estrutura.blocos_presentes.length})</p>
                <div className="space-y-1.5">
                  {analysis.estrutura.blocos_presentes.map((b, i) => (
                    <div key={i} className="flex gap-2 items-start rounded-lg p-2.5" style={{ background: "rgba(34,197,94,0.04)", border: "1px solid rgba(34,197,94,0.12)" }}>
                      <span className="text-xs font-bold flex-shrink-0 mt-0.5" style={{ color: getScoreColor(b.qualidade === "Forte" ? 9 : b.qualidade === "Médio" ? 6 : 3) }}>{b.qualidade}</span>
                      <div className="flex-1">
                        <p className="text-xs font-semibold text-white">{b.bloco}</p>
                        {b.trecho && <p className="text-xs mt-0.5 italic" style={{ color: "rgba(255,255,255,0.4)" }}>&ldquo;{b.trecho}&rdquo;</p>}
                      </div>
                      <button
                        onClick={() => setRewriteTarget({ bloco: b.bloco, trecho: b.trecho || "", nota: b.qualidade === "Forte" ? 8 : b.qualidade === "Médio" ? 6 : 4 })}
                        className="text-xs px-2 py-0.5 rounded flex-shrink-0"
                        style={{ color: "rgba(99,102,241,0.8)", border: "1px solid rgba(99,102,241,0.2)" }}
                        title="Reescrever este bloco"
                      >✏️</button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {analysis.estrutura.blocos_ausentes && analysis.estrutura.blocos_ausentes.length > 0 && (
              <div>
                <p className="text-xs font-bold mb-2" style={{ color: "#ef4444" }}>Blocos Ausentes ({analysis.estrutura.blocos_ausentes.length})</p>
                <div className="flex flex-wrap gap-1.5">
                  {analysis.estrutura.blocos_ausentes.map((b, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 rounded" style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}>{b}</span>
                  ))}
                </div>
              </div>
            )}
            <div className="grid grid-cols-3 gap-3 mt-3">
              <div className="rounded-lg p-3 text-center" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                <p className="text-2xl font-bold text-white">{analysis.estrutura.invalidacoes?.quantidade ?? 0}</p>
                <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>Invalidações</p>
              </div>
              <div className="rounded-lg p-3 text-center" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                <p className="text-2xl font-bold text-white">{analysis.estrutura.provas?.quantidade ?? 0}</p>
                <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>Provas</p>
              </div>
              <div className="rounded-lg p-3 text-center" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                <p className="text-2xl font-bold text-white">{analysis.estrutura.ctas?.quantidade ?? 0}</p>
                <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>CTAs</p>
              </div>
            </div>
            {/* Ciclos de invalidação */}
            {analysis.estrutura.invalidacoes?.ciclos && analysis.estrutura.invalidacoes.ciclos.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-bold mb-2" style={{ color: "rgba(255,255,255,0.5)" }}>Ciclos de Invalidação</p>
                <div className="space-y-2">
                  {analysis.estrutura.invalidacoes.ciclos.map((c, i) => {
                    const qColor = c.qualidade === "Forte" ? "#22c55e" : c.qualidade === "Médio" ? "#eab308" : "#ef4444";
                    return (
                      <div key={i} className="rounded-lg p-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          {c.qualidade && <span className="text-xs font-bold px-1.5 py-0.5 rounded" style={{ background: `${qColor}15`, color: qColor }}>{c.qualidade}</span>}
                          {c.tem_reason_why && <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.1)", color: "#818cf8" }}>RW: {c.reason_why_tipo || "sim"}</span>}
                          {c.conectada_ao_mup && <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(239,68,68,0.1)", color: "#fca5a5" }}>🧬 MUP</span>}
                        </div>
                        {c.solucoes_invalidadas && c.solucoes_invalidadas.length > 0 && (
                          <div className="flex flex-wrap gap-1 mb-1">
                            {c.solucoes_invalidadas.map((s, si) => <span key={si} className="text-xs line-through" style={{ color: "rgba(255,255,255,0.35)" }}>{s}</span>)}
                          </div>
                        )}
                        {c.trecho && <p className="text-xs italic" style={{ color: "rgba(255,255,255,0.45)" }}>&ldquo;{c.trecho}&rdquo;</p>}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            {/* Invalidações sugeridas */}
            {analysis.estrutura.invalidacoes?.invalidacoes_sugeridas && analysis.estrutura.invalidacoes.invalidacoes_sugeridas.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-bold mb-2" style={{ color: "#818cf8" }}>Invalidações Sugeridas</p>
                <div className="space-y-2">
                  {analysis.estrutura.invalidacoes.invalidacoes_sugeridas.map((s, i) => (
                    <div key={i} className="rounded-lg p-3" style={{ background: "rgba(99,102,241,0.05)", border: "1px solid rgba(99,102,241,0.2)" }}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <p className="text-xs font-semibold mb-0.5" style={{ color: "#a78bfa" }}>→ {s.solucao_a_invalidar}</p>
                          {s.reason_why && <p className="text-xs mb-1" style={{ color: "rgba(255,255,255,0.45)" }}>RW: {s.reason_why}</p>}
                          <p className="text-xs" style={{ color: "rgba(255,255,255,0.7)", fontStyle: "italic" }}>&ldquo;{s.texto_sugerido}&rdquo;</p>
                        </div>
                        <CopyButton text={s.texto_sugerido} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {analysis.estrutura.provas?.tipos_encontrados && analysis.estrutura.provas.tipos_encontrados.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {analysis.estrutura.provas.tipos_encontrados.map((t, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.1)", color: "#a78bfa" }}>{t}</span>
                ))}
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* ── BULLETS ── */}
      {analysis.bullets && (
        <CollapsibleSection title="Bullets Identificados" emoji="💎" defaultOpen={false}>
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2 mb-2">
              {[
                { label: "Nomeação proprietária", ok: analysis.bullets.tem_nomeacao_proprietaria },
                { label: "Especificidade", ok: analysis.bullets.tem_especificidade },
                { label: "Parênteses de consequência", ok: analysis.bullets.tem_parenteses_consequencia },
              ].map(({ label, ok }) => (
                <span key={label} className="text-xs px-2 py-0.5 rounded-full" style={{ background: ok ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.08)", color: ok ? "#22c55e" : "#ef4444", border: `1px solid ${ok ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.15)"}` }}>
                  {ok ? "✓" : "✕"} {label}
                </span>
              ))}
            </div>
            {analysis.bullets.encontrados && analysis.bullets.encontrados.map((b, i) => (
              <div key={i} className="rounded-lg p-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold" style={{ color: "#818cf8" }}>{b.tipo}</span>
                  <span className="text-xs" style={{ color: getScoreColor(b.qualidade === "Forte" ? 9 : b.qualidade === "Médio" ? 6 : 3) }}>{b.qualidade}</span>
                </div>
                <p className="text-sm" style={{ color: "rgba(255,255,255,0.75)" }}>{b.texto}</p>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* ── LINGUAGEM VISCERAL ── */}
      {analysis.linguagem_detalhada && (
        <CollapsibleSection title="Linguagem Visceral" emoji="🔥" defaultOpen={false}>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold px-3 py-1 rounded-full" style={{
                  background: analysis.linguagem_detalhada.nivel === "Visceral" ? "rgba(34,197,94,0.12)" : analysis.linguagem_detalhada.nivel === "Coloquial" ? "rgba(234,179,8,0.12)" : "rgba(239,68,68,0.12)",
                  color: analysis.linguagem_detalhada.nivel === "Visceral" ? "#22c55e" : analysis.linguagem_detalhada.nivel === "Coloquial" ? "#eab308" : "#ef4444",
                  border: `1px solid ${analysis.linguagem_detalhada.nivel === "Visceral" ? "rgba(34,197,94,0.3)" : analysis.linguagem_detalhada.nivel === "Coloquial" ? "rgba(234,179,8,0.3)" : "rgba(239,68,68,0.3)"}`,
                }}>{analysis.linguagem_detalhada.nivel}</span>
                {analysis.linguagem_detalhada.nota_visceral !== undefined && (
                  <span className="text-sm font-bold" style={{ color: getScoreColor(analysis.linguagem_detalhada.nota_visceral) }}>
                    {analysis.linguagem_detalhada.nota_visceral}/10
                  </span>
                )}
              </div>
              {analysis.linguagem_detalhada.trechos_genericos && analysis.linguagem_detalhada.trechos_genericos.filter(t => t.original).length > 0 && (
                <div>
                  <p className="text-xs font-bold mb-2" style={{ color: "rgba(255,255,255,0.5)" }}>Antes → Depois</p>
                  <div className="space-y-3">
                    {analysis.linguagem_detalhada.trechos_genericos.filter(t => t.original).map((t, i) => (
                      <div key={i} className="grid grid-cols-2 gap-2">
                        <div className="rounded-lg p-3" style={{ background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.15)" }}>
                          <p className="text-xs mb-1" style={{ color: "#ef4444" }}>Original</p>
                          <p className="text-xs" style={{ color: "rgba(255,255,255,0.55)" }}>{t.original}</p>
                        </div>
                        <div className="rounded-lg p-3" style={{ background: "rgba(34,197,94,0.05)", border: "1px solid rgba(34,197,94,0.15)" }}>
                          <div className="flex items-start justify-between gap-1">
                            <p className="text-xs mb-1" style={{ color: "#22c55e" }}>Visceral</p>
                            <CopyButton text={t.reescrita_visceral} />
                          </div>
                          <p className="text-xs" style={{ color: "rgba(255,255,255,0.8)" }}>{t.reescrita_visceral}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {analysis.linguagem_detalhada.verbos_fracos_encontrados && analysis.linguagem_detalhada.verbos_fracos_encontrados.length > 0 && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-bold mb-2" style={{ color: "#ef4444" }}>Verbos Fracos</p>
                    <div className="flex flex-wrap gap-1.5">
                      {analysis.linguagem_detalhada.verbos_fracos_encontrados.map((v, i) => (
                        <span key={i} className="text-xs px-2 py-0.5 rounded" style={{ background: "rgba(239,68,68,0.08)", color: "#fca5a5" }}>{v}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-bold mb-2" style={{ color: "#22c55e" }}>Substitutos Fortes</p>
                    <div className="flex flex-wrap gap-1.5">
                      {(analysis.linguagem_detalhada.verbos_fortes_sugeridos || []).map((v, i) => (
                        <span key={i} className="text-xs px-2 py-0.5 rounded" style={{ background: "rgba(34,197,94,0.08)", color: "#86efac" }}>{v}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </CollapsibleSection>
      )}

      {/* ── VISUAL ── */}
      {analysis.visual && (
        <CollapsibleSection title="Análise Visual" emoji="🎬" defaultOpen={false}>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Formato", value: analysis.visual.formato },
              { label: "Presença Humana", value: analysis.visual.tipo_presenca || analysis.visual.presenca_humana },
              { label: "Ritmo de Edição", value: analysis.visual.ritmo_edicao },
              { label: "CTA Visual", value: analysis.visual.cta_visual },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg p-3" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                <p className="text-xs mb-1" style={{ color: "rgba(255,255,255,0.4)" }}>{label}</p>
                <p className="text-sm font-semibold text-white">{value || "—"}</p>
              </div>
            ))}
            {analysis.visual.tipos_texto && analysis.visual.tipos_texto.length > 0 && (
              <div className="col-span-2 flex flex-wrap gap-1.5">
                {analysis.visual.tipos_texto.map((t, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.1)", color: "#818cf8" }}>{t}</span>
                ))}
              </div>
            )}
            {analysis.visual.hook_visual_descricao && (
              <div className="col-span-2">
                <p className="text-xs mb-1" style={{ color: "rgba(255,255,255,0.4)" }}>Hook visual (primeiros 3s)</p>
                <p className="text-sm" style={{ color: "rgba(255,255,255,0.7)" }}>{analysis.visual.hook_visual_descricao}</p>
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* ── PONTOS FORTES / FRACOS ── */}
      {analysis.diagnostico && (
        <CollapsibleSection title="Pontos Fortes & Fracos" emoji="⚖️" defaultOpen={true}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-bold mb-2" style={{ color: "#22c55e" }}>Pontos Fortes</p>
              <div className="space-y-1.5">
                {(analysis.diagnostico.pontos_fortes || []).map((p, i) => (
                  <div key={i} className="flex gap-2 items-start">
                    <span style={{ color: "#22c55e", flexShrink: 0, marginTop: 1 }}>•</span>
                    <p className="text-sm" style={{ color: "rgba(255,255,255,0.75)" }}>{p}</p>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-bold mb-2" style={{ color: "#ef4444" }}>Pontos Fracos</p>
              <div className="space-y-1.5">
                {(analysis.diagnostico.pontos_fracos || []).map((p, i) => (
                  <div key={i} className="flex gap-2 items-start">
                    <span style={{ color: "#ef4444", flexShrink: 0, marginTop: 1 }}>•</span>
                    <p className="text-sm" style={{ color: "rgba(255,255,255,0.75)" }}>{p}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CollapsibleSection>
      )}

      {/* ── GERADOR ── */}
      {analysis.gerador && (
        <div className="space-y-4">
          {/* Hooks alternativos */}
          {analysis.gerador.hooks_alternativos && analysis.gerador.hooks_alternativos.filter(h => h.hook).length > 0 && (
            <div className="card p-5">
              <p className="section-title mb-1">🎯 5 Hooks Alternativos</p>
              <p className="text-xs mb-4" style={{ color: "rgba(255,255,255,0.35)" }}>Gerados com ângulos diferentes do hook original</p>
              <div className="space-y-3">
                {analysis.gerador.hooks_alternativos.filter(h => h.hook).map((h, i) => {
                  const camadaColors: Record<string, { bg: string; color: string }> = {
                    "Desejo": { bg: "rgba(59,130,246,0.15)", color: "#60a5fa" },
                    "Funcional": { bg: "rgba(34,197,94,0.15)", color: "#4ade80" },
                    "Dimensional": { bg: "rgba(139,92,246,0.15)", color: "#a78bfa" },
                    "Emocional": { bg: "rgba(236,72,153,0.15)", color: "#f472b6" },
                    "Livre": { bg: "rgba(107,114,128,0.15)", color: "#9ca3af" },
                  };
                  const cc = h.beneficio_camada ? (camadaColors[h.beneficio_camada] || camadaColors["Livre"]) : null;
                  return (
                    <div key={i} className="rounded-xl p-4" style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.15)" }}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.15)", color: "#818cf8" }}>{h.angulo}</span>
                          {cc && <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ background: cc.bg, color: cc.color }}>{h.beneficio_camada}</span>}
                          {h.teasing_usado && <span className="text-xs italic px-2 py-0.5 rounded" style={{ background: "rgba(234,179,8,0.08)", color: "#eab308" }}>⛏ {h.teasing_usado}</span>}
                        </div>
                        <CopyButton text={h.hook} />
                      </div>
                      <p className="text-sm font-semibold" style={{ color: "#e2e8f0", lineHeight: 1.5 }}>{h.hook}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Bullets sugeridos */}
          {analysis.gerador.bullets_sugeridos && analysis.gerador.bullets_sugeridos.filter(b => b.bullet).length > 0 && (
            <div className="card p-5">
              <p className="section-title mb-1">💎 5 Bullets Sugeridos</p>
              <p className="text-xs mb-4" style={{ color: "rgba(255,255,255,0.35)" }}>Refinados com especificidade + curiosidade + benefício</p>
              <div className="space-y-3">
                {analysis.gerador.bullets_sugeridos.filter(b => b.bullet).map((b, i) => {
                  const esferaIcons: Record<string, string> = { "Social": "👥", "Íntima": "💕", "Profissional": "💼", "Digital": "📱", "Pessoal": "🪞" };
                  const esferaColors: Record<string, string> = { "Social": "#38bdf8", "Íntima": "#f472b6", "Profissional": "#facc15", "Digital": "#34d399", "Pessoal": "#c084fc" };
                  return (
                    <div key={i} className="rounded-xl p-4" style={{ background: "rgba(139,92,246,0.06)", border: "1px solid rgba(139,92,246,0.15)" }}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: "rgba(139,92,246,0.15)", color: "#a78bfa" }}>{b.tipo}</span>
                          {b.esfera && <span className="text-xs font-semibold" style={{ color: esferaColors[b.esfera] || "#9ca3af" }}>{esferaIcons[b.esfera] || ""} {b.esfera}</span>}
                          {b.posicao_ideal && <span className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>{b.posicao_ideal}</span>}
                          {b.tem_nomeacao && <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(34,197,94,0.1)", color: "#4ade80" }}>©</span>}
                          {b.tem_parenteses && <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.1)", color: "#818cf8" }}>()</span>}
                        </div>
                        <CopyButton text={b.bullet} />
                      </div>
                      <p className="text-sm font-semibold" style={{ color: "#e2e8f0", lineHeight: 1.5 }}>{b.bullet}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Extras */}
          {(analysis.gerador.mup_alternativo || analysis.gerador.msol_alternativo || analysis.gerador.future_pacing_sugerido) && (
            <div className="card p-5">
              <p className="section-title mb-4">🔧 Sugestões Extras</p>
              <div className="space-y-3">
                {analysis.gerador.mup_alternativo && (
                  <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold" style={{ color: "#eab308" }}>MUP Alternativo</span>
                      <CopyButton text={analysis.gerador.mup_alternativo} />
                    </div>
                    <p className="text-sm" style={{ color: "rgba(255,255,255,0.75)" }}>{analysis.gerador.mup_alternativo}</p>
                  </div>
                )}
                {analysis.gerador.msol_alternativo && (
                  <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold" style={{ color: "#22c55e" }}>MSOL Alternativo</span>
                      <CopyButton text={analysis.gerador.msol_alternativo} />
                    </div>
                    <p className="text-sm" style={{ color: "rgba(255,255,255,0.75)" }}>{analysis.gerador.msol_alternativo}</p>
                  </div>
                )}
                {analysis.gerador.future_pacing_sugerido && (
                  <div className="rounded-xl p-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold" style={{ color: "#818cf8" }}>Future Pacing</span>
                      <CopyButton text={analysis.gerador.future_pacing_sugerido} />
                    </div>
                    <p className="text-sm" style={{ color: "rgba(255,255,255,0.75)" }}>{analysis.gerador.future_pacing_sugerido}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Feedback Form ────────────────────────────────────────────────────────────

function FeedbackForm({
  analysis,
  videoName,
  onSaved,
}: {
  analysis: AnalysisResult;
  videoName: string;
  onSaved: () => void;
}) {
  const [resultado, setResultado] = useState("");
  const [gasto, setGasto] = useState("");
  const [roas, setRoas] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    if (!resultado) return;
    setSaving(true);
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          videoName,
          notaGemini: analysis.scorecard?.nota_geral ?? 0,
          formato: analysis.visual?.formato || "",
          hookAvaliacao: analysis.analise_hook?.forca || "",
          ctaAvaliacao: analysis.visual?.cta_visual || "",
          resultado,
          gasto,
          roas,
          observacoes,
        }),
      });
      setSaved(true);
      onSaved();
    } finally {
      setSaving(false);
    }
  };

  const resultadoOpts = ["Escalou", "Bom", "Médio", "Ruim", "Morreu rápido"];
  const resultadoColors: Record<string, string> = {
    "Escalou": "#22c55e",
    "Bom": "#86efac",
    "Médio": "#eab308",
    "Ruim": "#f97316",
    "Morreu rápido": "#ef4444",
  };

  if (saved) {
    return (
      <div
        className="card p-6 text-center animate-fade-in"
        style={{ border: "1px solid rgba(34,197,94,0.3)", background: "rgba(34,197,94,0.05)" }}
      >
        <p className="text-2xl mb-2">✅</p>
        <p className="font-semibold text-white">Resultado registrado!</p>
        <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.45)" }}>
          Próximas análises serão calibradas com esse histórico.
        </p>
      </div>
    );
  }

  return (
    <div className="card p-6 animate-fade-in">
      <div className="flex items-center gap-2 mb-5">
        <span className="text-xl">📊</span>
        <div>
          <p className="font-bold text-white">Registrar Resultado do Anúncio</p>
          <p className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
            Isso treina a IA para analisar seus próximos criativos com mais precisão
          </p>
        </div>
      </div>

      {/* Resultado */}
      <div className="mb-4">
        <p className="section-title mb-2">Como foi o desempenho?</p>
        <div className="flex flex-wrap gap-2">
          {resultadoOpts.map((opt) => (
            <button
              key={opt}
              onClick={() => setResultado(opt)}
              className="px-4 py-2 rounded-lg text-sm font-semibold transition-all"
              style={{
                border: `1px solid ${resultado === opt ? resultadoColors[opt] : "rgba(255,255,255,0.1)"}`,
                background: resultado === opt ? `${resultadoColors[opt]}20` : "transparent",
                color: resultado === opt ? resultadoColors[opt] : "rgba(255,255,255,0.5)",
              }}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Gasto + ROAS */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <p className="section-title mb-1">Gasto total</p>
          <input
            type="text"
            placeholder="Ex: R$500"
            value={gasto}
            onChange={(e) => setGasto(e.target.value)}
            className="w-full px-3 py-2 rounded-lg text-sm"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "#e2e8f0",
            }}
          />
        </div>
        <div>
          <p className="section-title mb-1">ROAS / Resultado</p>
          <input
            type="text"
            placeholder="Ex: 3.5x ou R$2.000"
            value={roas}
            onChange={(e) => setRoas(e.target.value)}
            className="w-full px-3 py-2 rounded-lg text-sm"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "#e2e8f0",
            }}
          />
        </div>
      </div>

      {/* Observações */}
      <div className="mb-5">
        <p className="section-title mb-1">O que você percebeu? (opcional)</p>
        <textarea
          placeholder="Ex: O hook foi muito direto, público reagiu bem ao depoimento..."
          value={observacoes}
          onChange={(e) => setObservacoes(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 rounded-lg text-sm resize-none"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.1)",
            color: "#e2e8f0",
          }}
        />
      </div>

      <button
        onClick={handleSave}
        disabled={!resultado || saving}
        className="w-full py-3 rounded-xl font-bold text-white transition-all"
        style={{
          background: !resultado ? "rgba(99,102,241,0.2)" : "linear-gradient(135deg,#6366f1,#8b5cf6)",
          cursor: !resultado ? "not-allowed" : "pointer",
        }}
      >
        {saving ? "Salvando..." : "Salvar Resultado"}
      </button>
    </div>
  );
}

// ─── Histórico Panel ──────────────────────────────────────────────────────────

function HistoricoPanel({ onClose }: { onClose: () => void }) {
  const [entries, setEntries] = useState<FeedbackEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/feedback")
      .then((r) => r.json())
      .then((data) => setEntries(Array.isArray(data) ? data : []))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id: string) => {
    await fetch("/api/feedback", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    setEntries((prev) => prev.filter((e) => e.id !== id));
  };

  const resultadoColors: Record<string, string> = {
    "Escalou": "#22c55e",
    "Bom": "#86efac",
    "Médio": "#eab308",
    "Ruim": "#f97316",
    "Morreu rápido": "#ef4444",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4"
      style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl card p-6 animate-slide-up overflow-y-auto"
        style={{ maxHeight: "80vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="font-bold text-white text-lg">Histórico de Criativos</h2>
            <p className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
              {entries.length} resultado(s) registrado(s)
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-sm px-3 py-1 rounded-lg"
            style={{ border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.5)" }}
          >
            Fechar
          </button>
        </div>

        {loading && (
          <p className="text-center py-8" style={{ color: "rgba(255,255,255,0.4)" }}>
            Carregando...
          </p>
        )}

        {!loading && entries.length === 0 && (
          <p className="text-center py-8" style={{ color: "rgba(255,255,255,0.3)" }}>
            Nenhum resultado registrado ainda.
          </p>
        )}

        {/* Padrões detectados (min 5 ads) */}
        {entries.length >= 5 && (() => {
          const escalaram = entries.filter(e => e.resultado === "Escalou" || e.resultado === "Bom");
          const ruims = entries.filter(e => e.resultado === "Ruim" || e.resultado === "Morreu rápido");
          const avgNota = (arr: FeedbackEntry[]) => arr.length ? (arr.reduce((s, e) => s + e.notaGemini, 0) / arr.length).toFixed(1) : "—";
          const topFormato = (arr: FeedbackEntry[]) => {
            const counts: Record<string, number> = {};
            arr.forEach(e => { if (e.formato) counts[e.formato] = (counts[e.formato] || 0) + 1; });
            return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || "—";
          };
          return (
            <div className="mb-4 rounded-xl p-4" style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.2)" }}>
              <p className="text-sm font-bold text-white mb-3">📊 Padrões Identificados</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg p-3" style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.15)" }}>
                  <p className="text-xs font-bold mb-1" style={{ color: "#4ade80" }}>✅ Funcionaram ({escalaram.length})</p>
                  <p className="text-xs" style={{ color: "rgba(255,255,255,0.6)" }}>Nota média: {avgNota(escalaram)}/10</p>
                  <p className="text-xs" style={{ color: "rgba(255,255,255,0.6)" }}>Formato top: {topFormato(escalaram)}</p>
                </div>
                <div className="rounded-lg p-3" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)" }}>
                  <p className="text-xs font-bold mb-1" style={{ color: "#f87171" }}>❌ Não funcionaram ({ruims.length})</p>
                  <p className="text-xs" style={{ color: "rgba(255,255,255,0.6)" }}>Nota média: {avgNota(ruims)}/10</p>
                  <p className="text-xs" style={{ color: "rgba(255,255,255,0.6)" }}>Formato top: {topFormato(ruims)}</p>
                </div>
              </div>
              {escalaram.length > 0 && ruims.length > 0 && (
                <p className="text-xs mt-3 italic" style={{ color: "rgba(255,255,255,0.45)" }}>
                  {Number(avgNota(escalaram)) > Number(avgNota(ruims))
                    ? `Criativos com nota acima de ${avgNota(escalaram)} tendem a performar melhor nesta conta.`
                    : `Alta nota não garante resultado — analise o hook e formato.`}
                </p>
              )}
            </div>
          );
        })()}

        <div className="space-y-3">
          {entries.map((e) => (
            <div
              key={e.id}
              className="p-4 rounded-xl"
              style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span
                      className="badge"
                      style={{
                        background: `${resultadoColors[e.resultado] || "#6366f1"}20`,
                        color: resultadoColors[e.resultado] || "#818cf8",
                        border: `1px solid ${resultadoColors[e.resultado] || "#6366f1"}40`,
                      }}
                    >
                      {e.resultado}
                    </span>
                    {e.formato && <span className="badge badge-default">{e.formato}</span>}
                    <span className="text-xs font-mono" style={{ color: "rgba(255,255,255,0.35)" }}>
                      Nota: {e.notaGemini}/10
                    </span>
                  </div>
                  <p className="text-sm font-medium text-white truncate">{e.videoName}</p>
                  <div className="flex gap-4 mt-1 text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
                    {e.gasto && <span>Gasto: {e.gasto}</span>}
                    {e.roas && <span>ROAS: {e.roas}</span>}
                    <span>{new Date(e.date).toLocaleDateString("pt-BR")}</span>
                  </div>
                  {e.observacoes && (
                    <p className="text-xs mt-2 italic" style={{ color: "rgba(255,255,255,0.5)" }}>
                      &ldquo;{e.observacoes}&rdquo;
                    </p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(e.id)}
                  className="text-xs px-2 py-1 rounded flex-shrink-0"
                  style={{ color: "rgba(239,68,68,0.6)", border: "1px solid rgba(239,68,68,0.2)" }}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Script Generator Panel ──────────────────────────────────────────────────

interface SavedSession {
  transcription: string;
  analysis: AnalysisResult;
  sourceName: string;
  date: string;
}

interface GeneratedScript {
  hook: string;
  body: string;
  cta: string;
  script_completo: string;
  dicas_gravacao: string[];
}

function ScriptGeneratorPanel({ onClose }: { onClose: () => void }) {
  const [session, setSession] = useState<SavedSession | null>(null);
  const [script, setScript] = useState<GeneratedScript | null>(null);
  const [editedScript, setEditedScript] = useState("");
  const [generatingScript, setGeneratingScript] = useState(false);
  const [generatingAudio, setGeneratingAudio] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    try {
      const raw = localStorage.getItem("lastAnalysis");
      if (raw) setSession(JSON.parse(raw));
    } catch {
      // ignore
    }
  }, []);

  const handleGenerateScript = async () => {
    if (!session) return;
    setGeneratingScript(true);
    setError("");
    setScript(null);
    setAudioUrl(null);
    try {
      const res = await fetch("/api/generate-script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcription: session.transcription, analysis: session.analysis }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erro ao gerar script");
      setScript(data.script);
      setEditedScript(data.script.script_completo || "");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro desconhecido");
    } finally {
      setGeneratingScript(false);
    }
  };

  const handleGenerateAudio = async () => {
    const text = editedScript.trim();
    if (!text) return;
    setGeneratingAudio(true);
    setError("");
    setAudioUrl(null);
    try {
      const res = await fetch("/api/generate-audio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Erro ao gerar áudio");
      }
      const blob = await res.blob();
      setAudioUrl(URL.createObjectURL(blob));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro desconhecido");
    } finally {
      setGeneratingAudio(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-10 px-4 pb-10"
      style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(8px)", overflowY: "auto" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl card p-6 animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="font-bold text-white text-lg">Gerador de Script + Narração</h2>
            <p className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
              Baseado na última análise de criativo
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-sm px-3 py-1.5 rounded-lg"
            style={{ color: "rgba(255,255,255,0.4)", border: "1px solid rgba(255,255,255,0.1)" }}
          >
            ✕
          </button>
        </div>

        {!session ? (
          <div className="text-center py-10">
            <p className="text-4xl mb-3">🎙️</p>
            <p className="font-semibold text-white mb-1">Nenhuma análise encontrada</p>
            <p className="text-sm" style={{ color: "rgba(255,255,255,0.4)" }}>
              Faça uma análise de criativo primeiro para gerar um novo script.
            </p>
          </div>
        ) : (
          <>
            {/* Last analysis info */}
            <div
              className="rounded-xl p-4 mb-5"
              style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)" }}
            >
              <p className="text-xs mb-1" style={{ color: "rgba(255,255,255,0.4)" }}>Última análise</p>
              <p className="font-semibold text-white text-sm truncate">{session.sourceName}</p>
              <p className="text-xs mt-1" style={{ color: "rgba(255,255,255,0.35)" }}>
                {new Date(session.date).toLocaleString("pt-BR")} ·{" "}
                Nota {session.analysis.scorecard?.nota_geral ?? 0}/10 ·{" "}
                {session.analysis.visual?.formato || session.analysis.scorecard?.classificacao || ""}
              </p>
              {session.transcription && session.transcription !== "[Transcrição não disponível]" && (
                <p className="text-xs mt-2 italic line-clamp-2" style={{ color: "rgba(255,255,255,0.45)" }}>
                  &ldquo;{session.transcription.slice(0, 120)}...&rdquo;
                </p>
              )}
            </div>

            {/* Generate script button */}
            {!script && (
              <button
                onClick={handleGenerateScript}
                disabled={generatingScript}
                className="w-full py-3 rounded-xl font-bold text-white transition-all mb-4"
                style={{
                  background: generatingScript ? "rgba(99,102,241,0.3)" : "linear-gradient(135deg,#6366f1,#8b5cf6)",
                  cursor: generatingScript ? "not-allowed" : "pointer",
                }}
              >
                {generatingScript ? "Gerando script..." : "✨ Gerar Script Melhorado"}
              </button>
            )}

            {/* Script result */}
            {script && (
              <div className="space-y-4 mb-4">
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: "Hook", value: script.hook, color: "#6366f1" },
                    { label: "Body", value: script.body, color: "#8b5cf6" },
                    { label: "CTA", value: script.cta, color: "#a78bfa" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="rounded-xl p-3" style={{ background: "rgba(255,255,255,0.04)", border: `1px solid ${color}30` }}>
                      <p className="text-xs font-bold mb-1" style={{ color }}>{label}</p>
                      <p className="text-xs" style={{ color: "rgba(255,255,255,0.7)", lineHeight: 1.5 }}>{value}</p>
                    </div>
                  ))}
                </div>

                {script.dicas_gravacao?.length > 0 && (
                  <div className="rounded-xl p-3" style={{ background: "rgba(234,179,8,0.06)", border: "1px solid rgba(234,179,8,0.2)" }}>
                    <p className="text-xs font-bold mb-2" style={{ color: "#eab308" }}>Dicas de Gravação</p>
                    <ul className="space-y-1">
                      {script.dicas_gravacao.map((d, i) => (
                        <li key={i} className="text-xs flex gap-2" style={{ color: "rgba(255,255,255,0.6)" }}>
                          <span style={{ color: "#eab308" }}>•</span> {d}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div>
                  <p className="section-title mb-2">Script completo para narração</p>
                  <textarea
                    value={editedScript}
                    onChange={(e) => setEditedScript(e.target.value)}
                    rows={6}
                    className="w-full px-3 py-2 rounded-lg text-sm resize-none"
                    style={{
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(255,255,255,0.12)",
                      color: "#e2e8f0",
                      lineHeight: 1.6,
                    }}
                  />
                  <p className="text-xs mt-1" style={{ color: "rgba(255,255,255,0.3)" }}>
                    Você pode editar o texto antes de gerar o áudio.
                  </p>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={handleGenerateScript}
                    disabled={generatingScript}
                    className="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all"
                    style={{
                      border: "1px solid rgba(99,102,241,0.3)",
                      color: "#818cf8",
                      background: "transparent",
                    }}
                  >
                    {generatingScript ? "Gerando..." : "↺ Gerar novo"}
                  </button>
                  <button
                    onClick={handleGenerateAudio}
                    disabled={generatingAudio || !editedScript.trim()}
                    className="flex-2 px-6 py-2.5 rounded-xl text-sm font-bold text-white transition-all"
                    style={{
                      background: generatingAudio ? "rgba(99,102,241,0.3)" : "linear-gradient(135deg,#6366f1,#8b5cf6)",
                      cursor: generatingAudio ? "not-allowed" : "pointer",
                      flexGrow: 2,
                    }}
                  >
                    {generatingAudio ? "Gerando narração..." : "🎙️ Gerar Narração com ElevenLabs"}
                  </button>
                </div>
              </div>
            )}

            {/* Audio player */}
            {audioUrl && (
              <div
                className="rounded-xl p-4 animate-fade-in"
                style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.2)" }}
              >
                <p className="text-sm font-semibold text-white mb-3">🎧 Narração gerada</p>
                <audio controls src={audioUrl} className="w-full mb-3" />
                <a
                  href={audioUrl}
                  download="narration.mp3"
                  className="inline-block text-sm px-4 py-2 rounded-lg font-semibold"
                  style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)" }}
                >
                  ⬇ Baixar MP3
                </a>
              </div>
            )}

            {error && (
              <div
                className="rounded-xl p-3 mt-3 animate-fade-in"
                style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)" }}
              >
                <p className="text-sm" style={{ color: "#ef4444" }}>{error}</p>
              </div>
            )}
          </>
        )}
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
  const [instagramUrl, setInstagramUrl] = useState("");
  const [step, setStep] = useState<Step>("idle");
  const [currentStep, setCurrentStep] = useState(0);
  const [transcription, setTranscription] = useState("");
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");
  const [manualTranscription, setManualTranscription] = useState("");
  const [showManual, setShowManual] = useState(false);
  const [showHistorico, setShowHistorico] = useState(false);
  const [showScript, setShowScript] = useState(false);
  const [showRemessa, setShowRemessa] = useState(false);
  const [feedbackSaved, setFeedbackSaved] = useState(false);

  // Save last analysis to localStorage for Script Generator
  useEffect(() => {
    if (!analysis) return;
    const sourceName =
      mode === "video" ? (videoFile?.name || "vídeo") :
      mode === "url" ? instagramUrl :
      `${imageFiles.length} imagem(ns)`;
    try {
      localStorage.setItem("lastAnalysis", JSON.stringify({
        transcription,
        analysis,
        sourceName,
        date: new Date().toISOString(),
      }));
    } catch {
      // ignore localStorage errors
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysis]);

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
    : mode === "url"
    ? ["Baixando vídeo...", "Transcrevendo áudio...", "Analisando criativo..."]
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
      } else if (mode === "url") {
        if (!instagramUrl.trim()) return;

        setCurrentStep(0);
        const res = await fetch("/api/analyze-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: instagramUrl.trim() }),
        });

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
    setInstagramUrl("");
    setStep("idle");
    setAnalysis(null);
    setError("");
    setTranscription("");
    setManualTranscription("");
    setShowManual(false);
    setFeedbackSaved(false);
    setShowScript(false);
    setShowRemessa(false);
  };

  const isProcessing = step === "uploading" || step === "transcribing" || step === "analyzing";
  const hasFile = mode === "video" ? !!videoFile : mode === "url" ? instagramUrl.trim().length > 0 : imageFiles.length > 0;

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
          <div className="flex items-center gap-2">
            {analysis && (
              <button
                onClick={() => setShowRemessa(true)}
                className="text-sm px-4 py-1.5 rounded-lg flex items-center gap-1.5"
                style={{ border: "1px solid rgba(34,197,94,0.3)", color: "#4ade80" }}
              >
                📦 Remessa
              </button>
            )}
            <button
              onClick={() => setShowScript(true)}
              className="text-sm px-4 py-1.5 rounded-lg flex items-center gap-1.5"
              style={{ border: "1px solid rgba(139,92,246,0.3)", color: "#a78bfa" }}
            >
              🎙️ Script
            </button>
            <button
              onClick={() => setShowHistorico(true)}
              className="text-sm px-4 py-1.5 rounded-lg flex items-center gap-1.5"
              style={{ border: "1px solid rgba(99,102,241,0.3)", color: "#818cf8" }}
            >
              📊 Histórico
            </button>
          </div>
        </div>
      </header>

      {showHistorico && <HistoricoPanel onClose={() => setShowHistorico(false)} />}
      {showScript && <ScriptGeneratorPanel onClose={() => setShowScript(false)} />}
      {showRemessa && analysis && <RemessaModal analysis={analysis} onClose={() => setShowRemessa(false)} />}

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
              {(["video", "images", "url"] as InputMode[]).map((m) => (
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
                  {m === "video" ? "🎬 Vídeo" : m === "url" ? "🔗 Link Instagram" : "🖼️ Screenshots"}
                </button>
              ))}
            </div>

            {/* Drop Zones / URL Input */}
            <div className="grid grid-cols-1 gap-4 mb-6">
              {mode === "url" ? (
                <div
                  className="card p-8 flex flex-col items-center gap-5"
                  style={{ minHeight: 200, justifyContent: "center" }}
                >
                  <div
                    className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl"
                    style={{ background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.3)" }}
                  >
                    🔗
                  </div>
                  <div className="w-full max-w-lg">
                    <p className="font-semibold text-white mb-1 text-center">Cole o link do post ou Reel do Instagram</p>
                    <p className="text-sm text-center mb-4" style={{ color: "rgba(255,255,255,0.4)" }}>
                      Funciona com posts públicos e Reels
                    </p>
                    <input
                      type="url"
                      placeholder="https://www.instagram.com/reel/..."
                      value={instagramUrl}
                      onChange={(e) => setInstagramUrl(e.target.value)}
                      disabled={isProcessing}
                      className="w-full px-4 py-3 rounded-xl text-sm"
                      style={{
                        background: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(99,102,241,0.3)",
                        color: "#e2e8f0",
                        outline: "none",
                      }}
                    />
                  </div>
                </div>
              ) : (
                <DropZone mode={mode} onFiles={mode === "video" ? handleVideoFiles : handleImageFiles} disabled={isProcessing} />
              )}
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
            {mode === "video" && videoFile && !isProcessing && (
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
                  {mode === "video" ? videoFile?.name : mode === "url" ? instagramUrl : `${imageFiles.length} imagem(ns)`}
                </p>
              </div>
            </div>
            <ResultsView analysis={analysis} transcription={transcription || manualTranscription} />

            {!feedbackSaved && (
              <FeedbackForm
                analysis={analysis}
                videoName={mode === "video" ? (videoFile?.name || "") : mode === "url" ? instagramUrl : `${imageFiles.length} imagem(ns)`}
                onSaved={() => setFeedbackSaved(true)}
              />
            )}
            {feedbackSaved && (
              <div
                className="card p-5 text-center animate-fade-in mb-8"
                style={{ border: "1px solid rgba(34,197,94,0.3)", background: "rgba(34,197,94,0.05)" }}
              >
                <p className="font-semibold text-white">✅ Resultado registrado — próximas análises serão calibradas com esse histórico.</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
