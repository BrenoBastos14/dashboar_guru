import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";
import { existsSync } from "fs";
import { FeedbackEntry } from "../feedback/route";
import { buildDRPrompt, parseDRAnalysis } from "../../../lib/dr-prompt";

export const maxDuration = 120;

const GEMINI_API_KEY = process.env.GEMINI_API_KEY!;

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
        return { inline_data: { mime_type: mimeType, data: base64 } };
      })
    );

    // Load history and build context
    let historyContext = "";
    try {
      const DATA_DIR = process.env.VERCEL ? "/tmp" : join(process.cwd(), "data");
      const DB_PATH = join(DATA_DIR, "feedback.json");
      if (existsSync(DB_PATH)) {
        const history: FeedbackEntry[] = JSON.parse(await readFile(DB_PATH, "utf-8"));
        if (history.length > 0) {
          const escalaram = history.filter((h) => h.resultado === "Escalou" || h.resultado === "Bom");
          const naoFuncionaram = history.filter((h) => h.resultado === "Ruim" || h.resultado === "Morreu rápido");
          historyContext = `\n\n---\nCONTEXTO HISTÓRICO DESTA CONTA:\nTotal analisados: ${history.length}`;
          if (escalaram.length > 0) {
            historyContext += `\nFuncionaram: ${escalaram.map((h) => `${h.formato} (Hook:${h.hookAvaliacao}, ROAS:${h.roas})`).slice(0, 5).join(" | ")}`;
          }
          if (naoFuncionaram.length > 0) {
            historyContext += `\nNão funcionaram: ${naoFuncionaram.map((h) => `${h.formato} (Hook:${h.hookAvaliacao})`).slice(0, 5).join(" | ")}`;
          }
          historyContext += "\n---";
        }
      }
    } catch { /* ignore */ }

    const prompt = buildDRPrompt("[sem transcrição — analise apenas pelo visual das imagens]", historyContext);
    const parts = [...imageParts, { text: prompt }];

    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts }],
          generationConfig: { temperature: 0.4, maxOutputTokens: 12000 },
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
      analysis = parseDRAnalysis(analysisText);
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
