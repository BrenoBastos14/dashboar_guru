import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 120;

const GEMINI_API_KEY = process.env.GEMINI_API_KEY!;

const ANALYSIS_PROMPT = `Você é um especialista em análise de criativos de anúncios digitais para direct response marketing no Brasil.

Analise este vídeo/imagens de anúncio e retorne uma análise detalhada no seguinte formato JSON (responda APENAS o JSON puro, sem markdown, sem backticks, sem texto antes ou depois):

{
  "hook_visual": {
    "descricao": "Descreva o que acontece nos primeiros 3 segundos do vídeo",
    "elementos": ["lista dos elementos visuais usados no hook"],
    "avaliacao": "Forte/Médio/Fraco",
    "justificativa": "Por que essa avaliação"
  },
  "formato": {
    "tipo": "VSL / UGC / Talking Head / B-Roll / Motion Graphics / Misto",
    "descricao": "Descrição do formato geral do vídeo"
  },
  "presenca_humana": {
    "tem_rosto": true,
    "tipo": "Talking head / Pessoa em ação / Sem pessoa / Depoimento / etc",
    "descricao": "Detalhes sobre presença humana"
  },
  "texto_em_tela": {
    "tem_texto": true,
    "tipos": ["headline", "legenda", "bullet points", "CTA"],
    "descricao": "Como o texto é usado no vídeo, quais textos aparecem"
  },
  "cores_dominantes": {
    "cores": ["lista de cores predominantes"],
    "estilo_visual": "Descrição do estilo visual e paleta de cores"
  },
  "edicao": {
    "ritmo": "Rápido / Moderado / Lento",
    "transicoes": "Tipos de transições usadas",
    "cortes_por_minuto_estimado": "número estimado",
    "descricao": "Padrão geral de edição"
  },
  "cta_visual": {
    "tem_cta": true,
    "tipo": "Botão / Texto / Seta / Animação / etc",
    "descricao": "Como o CTA é apresentado visualmente"
  },
  "pontos_fortes": ["lista dos 3-5 pontos fortes do criativo"],
  "pontos_fracos": ["lista dos 2-4 pontos fracos ou oportunidades de melhoria"],
  "sugestoes": ["lista de 3-5 sugestões práticas para melhorar o criativo"],
  "nota_geral": {
    "score": "7",
    "justificativa": "Justificativa breve da nota"
  }
}`;

function getMimeType(filename: string): string {
  const ext = filename.toLowerCase().split(".").pop();
  switch (ext) {
    case "jpg":
    case "jpeg":
      return "image/jpeg";
    case "png":
      return "image/png";
    case "webp":
      return "image/webp";
    case "gif":
      return "image/gif";
    default:
      return "image/jpeg";
  }
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const images = formData.getAll("images") as File[];

    if (!images || images.length === 0) {
      return NextResponse.json({ error: "Nenhuma imagem enviada" }, { status: 400 });
    }

    // Convert images to base64 inline data
    const imageParts = await Promise.all(
      images.map(async (img) => {
        const bytes = await img.arrayBuffer();
        const base64 = Buffer.from(bytes).toString("base64");
        const mimeType = getMimeType(img.name);
        return {
          inline_data: {
            mime_type: mimeType,
            data: base64,
          },
        };
      })
    );

    // Build Gemini request with all images + prompt
    const parts = [...imageParts, { text: ANALYSIS_PROMPT }];

    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts }],
          generationConfig: { temperature: 0.4, maxOutputTokens: 4096 },
        }),
      }
    );

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Erro na análise do Gemini: ${err}`);
    }

    const data = await res.json();
    const analysisText = data.candidates?.[0]?.content?.parts?.[0]?.text || "";

    let analysis: Record<string, unknown>;
    try {
      const cleaned = analysisText
        .replace(/^```json\s*/i, "")
        .replace(/^```\s*/i, "")
        .replace(/\s*```$/i, "")
        .trim();
      analysis = JSON.parse(cleaned);
    } catch {
      analysis = { raw: analysisText };
    }

    return NextResponse.json({ analysis });
  } catch (error: unknown) {
    console.error("Erro na análise de imagens:", error);
    const message = error instanceof Error ? error.message : "Erro desconhecido";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
