import { NextRequest, NextResponse } from "next/server";
import {
  tournamentAdversarialPrompt,
  tournamentSynthesizePrompt,
  tournamentJudgePrompt,
  TournamentTipo,
} from "../../../lib/dr-prompt";

export const maxDuration = 120;

const GEMINI_API_KEY = process.env.GEMINI_API_KEY!;
const MODEL = "gemini-2.5-flash-lite";
const MAX_ROUNDS = 3;
const NUM_JUDGES = 3;

interface RoundLog {
  round: number;
  versions: { A: string; B: string; AB: string };
  scores: { A: number; B: number; AB: number };
  winner: "A" | "B" | "AB";
  motivos: string[];
}

async function gemini(prompt: string, temperature = 0.8, maxTokens = 1500): Promise<string> {
  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature, maxOutputTokens: maxTokens },
      }),
    }
  );
  if (!res.ok) throw new Error(`Gemini: ${await res.text()}`);
  const data = await res.json();
  return (data.candidates?.[0]?.content?.parts?.[0]?.text || "").trim();
}

function parseJudgeResponse(raw: string): { ranking: number[]; motivo: string } {
  try {
    const cleaned = raw.replace(/```json\s*/gi, "").replace(/```\s*/g, "").trim();
    const start = cleaned.indexOf("{");
    const end = cleaned.lastIndexOf("}");
    if (start === -1 || end === -1) return { ranking: [1, 2, 3], motivo: "" };
    const parsed = JSON.parse(cleaned.slice(start, end + 1));
    const ranking = Array.isArray(parsed.ranking) && parsed.ranking.length === 3 ? parsed.ranking : [1, 2, 3];
    return { ranking, motivo: String(parsed.motivo || "") };
  } catch {
    return { ranking: [1, 2, 3], motivo: "" };
  }
}

function shuffle<T>(arr: T[]): T[] {
  const copy = [...arr];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function buildContext(analysis: Record<string, unknown>): string {
  const v = (analysis?.variaveis || {}) as Record<string, Record<string, unknown>>;
  const sub = (analysis?.sub_personas as Record<string, Record<string, unknown>> | undefined)?.atual || {};
  const teasings = (analysis?.teasings || {}) as Record<string, string[]>;
  const lines = [
    `Público: ${v.publico_alvo || "não especificado"}`,
    `Expert: ${(v.expert as Record<string, unknown>)?.nome || ""} (${(v.expert as Record<string, unknown>)?.camadas || 0} camadas)`,
    `MUP: ${(v.mup as Record<string, unknown>)?.descricao || ""}`,
    `MUF: ${(v.muf as Record<string, unknown>)?.descricao || ""}`,
    `MUS: ${(v.mus as Record<string, unknown>)?.nome || ""} — ${(v.mus as Record<string, unknown>)?.descricao || ""}`,
    `Promessa: ${(v.promessa as Record<string, unknown>)?.descricao || ""}`,
    `Sub-persona: ${sub.descricao || ""}`,
    `Medo dominante: ${sub.medo_dominante || ""}`,
    `Desejo dominante: ${sub.desejo_dominante || ""}`,
    `Teasings validados: ${[...(teasings.mup_teasings || []), ...(teasings.muf_teasings || []), ...(teasings.mus_teasings || [])].filter(Boolean).slice(0, 6).join(" | ")}`,
  ];
  return lines.filter((l) => l.split(": ")[1]?.replace(/^— */, "").trim()).join("\n");
}

export async function POST(req: NextRequest) {
  try {
    const { tipo, current_text, analysis } = (await req.json()) as {
      tipo: TournamentTipo;
      current_text: string;
      analysis: Record<string, unknown>;
    };

    if (!["hook", "body", "cta"].includes(tipo)) {
      return NextResponse.json({ error: "tipo inválido" }, { status: 400 });
    }
    if (!current_text?.trim()) {
      return NextResponse.json({ error: "current_text vazio" }, { status: 400 });
    }

    const context = buildContext(analysis || {});
    const rounds: RoundLog[] = [];

    let champion = current_text.trim();
    let previousWinnerId: "A" | "B" | "AB" | "" = "";
    let converged = false;

    for (let r = 1; r <= MAX_ROUNDS && !converged; r++) {
      // Gerar B (adversarial)
      const versionB = await gemini(
        tournamentAdversarialPrompt(tipo, champion, context),
        0.9,
        1200
      );

      // Gerar AB (síntese)
      const versionAB = await gemini(
        tournamentSynthesizePrompt(tipo, champion, versionB, context),
        0.7,
        1200
      );

      // Identificar versões e embaralhar para avaliação cega
      const versions: Array<{ id: "A" | "B" | "AB"; text: string }> = [
        { id: "A", text: champion },
        { id: "B", text: versionB },
        { id: "AB", text: versionAB },
      ];
      const shuffled = shuffle(versions);

      // 3 juízes em paralelo (avaliação cega)
      const judgePrompt = tournamentJudgePrompt(
        tipo,
        shuffled.map((v) => v.text),
        context
      );
      const judgeRaw = await Promise.all(
        Array.from({ length: NUM_JUDGES }).map(() => gemini(judgePrompt, 0.5, 400))
      );
      const judges = judgeRaw.map(parseJudgeResponse);

      // Borda count: 3pts para 1º, 2pts para 2º, 1pt para 3º
      const scores: Record<"A" | "B" | "AB", number> = { A: 0, B: 0, AB: 0 };
      for (const j of judges) {
        for (let rank = 0; rank < 3; rank++) {
          const shuffledPos = j.ranking[rank] - 1;
          if (shuffledPos < 0 || shuffledPos >= 3) continue;
          const id = shuffled[shuffledPos].id;
          scores[id] += 3 - rank;
        }
      }

      // Vencedor
      const winnerId = (Object.entries(scores) as Array<["A" | "B" | "AB", number]>).sort(
        (a, b) => b[1] - a[1]
      )[0][0];
      const winnerText = versions.find((v) => v.id === winnerId)!.text;

      rounds.push({
        round: r,
        versions: { A: champion, B: versionB, AB: versionAB },
        scores,
        winner: winnerId,
        motivos: judges.map((j) => j.motivo).filter(Boolean),
      });

      // Convergência: mesmo vencedor 2x seguidas
      if (previousWinnerId === winnerId) {
        converged = true;
      }
      previousWinnerId = winnerId;
      champion = winnerText;
    }

    return NextResponse.json({
      tipo,
      initial_text: current_text,
      final_text: champion,
      rounds,
      converged,
      total_rounds: rounds.length,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Erro desconhecido";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
