import { NextRequest, NextResponse } from "next/server";
import { REWRITE_BLOCK_PROMPT, parseDRAnalysis } from "../../../lib/dr-prompt";

export const maxDuration = 60;

const GEMINI_API_KEY = process.env.GEMINI_API_KEY!;

export async function POST(request: NextRequest) {
  try {
    const { bloco, trecho, nota, obs, variaveis } = await request.json();

    if (!bloco) return NextResponse.json({ error: "Bloco não informado" }, { status: 400 });

    const prompt = REWRITE_BLOCK_PROMPT(bloco, trecho || "", nota || 0, obs || "", variaveis || {});

    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.7, maxOutputTokens: 3000 },
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
      result = { bloco, versoes: [{ versao: 1, texto: raw, nota_estimada: 7, o_que_mudou: "" }] };
    }

    return NextResponse.json(result);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Erro desconhecido";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
