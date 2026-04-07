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
  analise_hook?: {
    angulo_identificado?: string;
    beneficio_tipo?: string;
    beneficio_camada?: string;
    forca?: string;
    texto_do_hook?: string;
    justificativa?: string;
  };
  estrutura?: {
    blocos_presentes?: { bloco: string; qualidade: string; trecho: string }[];
    blocos_ausentes?: string[];
    formato_usado?: string;
    invalidacoes?: { quantidade?: number; solucoes_invalidadas?: string[]; tem_reason_why_cientifico?: boolean };
    provas?: { tipos_encontrados?: string[]; quantidade?: number; qualidade?: string };
    ctas?: { quantidade?: number; distribuicao?: string; destino?: string };
  };
  bullets?: {
    encontrados?: { tipo: string; texto: string; qualidade: string }[];
    tem_nomeacao_proprietaria?: boolean;
    tem_especificidade?: boolean;
    tem_parenteses_consequencia?: boolean;
    qualidade_geral?: string;
  };
  visual?: {
    formato?: string;
    hook_visual_descricao?: string;
    presenca_humana?: string;
    tipo_presenca?: string;
    texto_em_tela?: boolean;
    tipos_texto?: string[];
    ritmo_edicao?: string;
    cta_visual?: string;
  };
  diagnostico?: {
    pontos_fortes?: string[];
    pontos_fracos?: string[];
    top3_melhorias?: { prioridade: number; acao: string; justificativa: string; impacto: string; framework: string }[];
  };
  gerador?: {
    hooks_alternativos?: { angulo: string; hook: string; beneficio_camada: string }[];
    bullets_sugeridos?: { tipo: string; bullet: string; posicao_ideal: string }[];
    mup_alternativo?: string;
    msol_alternativo?: string;
    future_pacing_sugerido?: string;
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

function ResultsView({ analysis, transcription }: { analysis: AnalysisResult; transcription?: string }) {
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

  return (
    <div className="animate-fade-in space-y-4">

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
                      <span className="text-xs font-bold flex-shrink-0" style={{ color: getScoreColor(b.qualidade === "Forte" ? 9 : b.qualidade === "Médio" ? 6 : 3) }}>{b.qualidade}</span>
                      <div>
                        <p className="text-xs font-semibold text-white">{b.bloco}</p>
                        {b.trecho && <p className="text-xs mt-0.5 italic" style={{ color: "rgba(255,255,255,0.4)" }}>&ldquo;{b.trecho}&rdquo;</p>}
                      </div>
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
                {analysis.gerador.hooks_alternativos.filter(h => h.hook).map((h, i) => (
                  <div key={i} className="rounded-xl p-4" style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.15)" }}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: "rgba(99,102,241,0.15)", color: "#818cf8" }}>{h.angulo}</span>
                        {h.beneficio_camada && <span className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>{h.beneficio_camada}</span>}
                      </div>
                      <CopyButton text={h.hook} />
                    </div>
                    <p className="text-sm font-semibold" style={{ color: "#e2e8f0", lineHeight: 1.5 }}>{h.hook}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bullets sugeridos */}
          {analysis.gerador.bullets_sugeridos && analysis.gerador.bullets_sugeridos.filter(b => b.bullet).length > 0 && (
            <div className="card p-5">
              <p className="section-title mb-1">💎 5 Bullets Sugeridos</p>
              <p className="text-xs mb-4" style={{ color: "rgba(255,255,255,0.35)" }}>Refinados com especificidade + curiosidade + benefício</p>
              <div className="space-y-3">
                {analysis.gerador.bullets_sugeridos.filter(b => b.bullet).map((b, i) => (
                  <div key={i} className="rounded-xl p-4" style={{ background: "rgba(139,92,246,0.06)", border: "1px solid rgba(139,92,246,0.15)" }}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: "rgba(139,92,246,0.15)", color: "#a78bfa" }}>{b.tipo}</span>
                        {b.posicao_ideal && <span className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>{b.posicao_ideal}</span>}
                      </div>
                      <CopyButton text={b.bullet} />
                    </div>
                    <p className="text-sm font-semibold" style={{ color: "#e2e8f0", lineHeight: 1.5 }}>{b.bullet}</p>
                  </div>
                ))}
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
                Nota {parseInt(session.analysis.nota_geral?.score || "0")}/10 ·{" "}
                {session.analysis.formato?.tipo || ""}
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
            <button
              onClick={() => setShowScript(true)}
              className="text-sm px-4 py-1.5 rounded-lg flex items-center gap-1.5"
              style={{ border: "1px solid rgba(139,92,246,0.3)", color: "#a78bfa" }}
            >
              🎙️ Gerar Script
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
