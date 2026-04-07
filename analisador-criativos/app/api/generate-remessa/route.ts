import { NextRequest, NextResponse } from "next/server";
import { REMESSA_PROMPT, parseDRAnalysis } from "../../../lib/dr-prompt";

export const maxDuration = 60;

const GEMINI_API_KEY = process.env.GEMINI_API_KEY!;

export async function POST(request: NextRequest) {
  try {
    const { analysis } = await request.json();

    if (!analysis) return NextResponse.json({ error: "Análise não fornecida" }, { status: 400 });

    // Build a compact context from the analysis
    const ctx = JSON.stringify({
      variaveis: analysis.variaveis,
      sub_personas: analysis.sub_personas,
      teasings: analysis.teasings,
      analise_hook: analysis.analise_hook,
      gerador: { hooks_alternativos: analysis.gerador?.hooks_alternativos },
      diagnostico: { pontos_fortes: analysis.diagnostico?.pontos_fortes },
    });

    const prompt = REMESSA_PROMPT(ctx);

    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.7, maxOutputTokens: 4000 },
        }),
      }
    );

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Erro no Gemini: ${err}`);
    }

    const data = await res.json();
    const raw = data.candidates?.[0]?.content?.parts?.[0]?.text || "";

    let result: Record<string, unknown>;
    try {
      result = parseDRAnalysis(raw);
    } catch {
      result = { remessa: [], logica_da_remessa: raw };
    }

    return NextResponse.json(result);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Erro desconhecido";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
