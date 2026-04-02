import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 60;

const GEMINI_API_KEY = process.env.GEMINI_API_KEY!;

export async function POST(request: NextRequest) {
  try {
    const { transcription, analysis } = await request.json();

    if (!transcription && !analysis) {
      return NextResponse.json({ error: "Transcrição ou análise necessária" }, { status: 400 });
    }

    const pontosFortes = (analysis?.pontos_fortes || []).join(", ");
    const pontosFracos = (analysis?.pontos_fracos || []).join(", ");
    const sugestoes = (analysis?.sugestoes || []).join(", ");
    const hookAvaliacao = analysis?.hook_visual?.avaliacao || "";
    const hookJustificativa = analysis?.hook_visual?.justificativa || "";
    const ctaDescricao = analysis?.cta_visual?.descricao || "";
    const formato = analysis?.formato?.tipo || "";

    const prompt = `Você é um especialista em copywriting para direct response no mercado brasileiro.

Com base na análise do criativo abaixo, crie um NOVO SCRIPT de anúncio melhorado.

---
TRANSCRIÇÃO ORIGINAL DO ÁUDIO:
${transcription || "[sem transcrição]"}

---
ANÁLISE DO CRIATIVO:
- Formato: ${formato}
- Hook visual (${hookAvaliacao}): ${hookJustificativa}
- CTA: ${ctaDescricao}
- Pontos fortes: ${pontosFortes}
- Pontos fracos: ${pontosFracos}
- Sugestões da IA: ${sugestoes}

---
INSTRUÇÕES:
1. Crie um script de anúncio otimizado, corrigindo os pontos fracos e mantendo o que funcionou
2. O script deve ser dividido em 3 partes claras: HOOK (primeiros 3 segundos), BODY (desenvolvimento) e CTA (chamada para ação)
3. Escreva em português brasileiro, linguagem natural e conversacional
4. O script deve ser adequado para narração em vídeo (sem marcações visuais, apenas o texto falado)
5. Duração sugerida: 30 a 60 segundos de fala
6. Retorne APENAS o JSON puro, sem markdown, sem backticks:

{
  "hook": "Texto do hook (3-5 segundos de fala)",
  "body": "Texto do corpo do anúncio",
  "cta": "Texto da chamada para ação",
  "script_completo": "Hook + body + cta unidos em um texto corrido, pronto para narração",
  "dicas_gravacao": ["dica 1", "dica 2", "dica 3"]
}`;

    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.7, maxOutputTokens: 2048 },
        }),
      }
    );

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Erro no Gemini: ${err}`);
    }

    const data = await res.json();
    const raw = data.candidates?.[0]?.content?.parts?.[0]?.text || "";

    let script: Record<string, unknown>;
    try {
      const cleaned = raw.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/i, "").trim();
      const start = cleaned.indexOf("{");
      const end = cleaned.lastIndexOf("}");
      script = JSON.parse(cleaned.slice(start, end + 1));
    } catch {
      script = { script_completo: raw, hook: "", body: "", cta: "", dicas_gravacao: [] };
    }

    return NextResponse.json({ script });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Erro desconhecido";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
