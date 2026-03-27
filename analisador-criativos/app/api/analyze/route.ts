import { NextRequest, NextResponse } from "next/server";
import { writeFile, unlink, readFile } from "fs/promises";
import { join } from "path";
import OpenAI from "openai";
import { createReadStream, existsSync } from "fs";
import { exec } from "child_process";
import { promisify } from "util";

export const maxDuration = 120;

const execAsync = promisify(exec);

const GEMINI_API_KEY = process.env.GEMINI_API_KEY!;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY!;

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

async function extractAudioWithFfmpeg(videoPath: string, audioPath: string): Promise<void> {
  // Try system ffmpeg first
  try {
    await execAsync(`ffmpeg -i "${videoPath}" -vn -acodec libmp3lame -q:a 4 "${audioPath}" -y 2>&1`);
    return;
  } catch {
    // ffmpeg not found in PATH, try ffmpeg-static path
  }

  // Try ffmpeg-static
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const ffmpegPath = (await import("ffmpeg-static")).default;
    if (ffmpegPath) {
      await execAsync(`"${ffmpegPath}" -i "${videoPath}" -vn -acodec libmp3lame -q:a 4 "${audioPath}" -y 2>&1`);
      return;
    }
  } catch {
    // ffmpeg-static not available
  }

  throw new Error("FFmpeg não disponível. Instale o ffmpeg no servidor.");
}

async function uploadToGemini(videoPath: string, mimeType: string): Promise<{ name: string; uri: string }> {
  const videoBuffer = await readFile(videoPath);

  const uploadRes = await fetch(
    `https://generativelanguage.googleapis.com/upload/v1beta/files?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: {
        "X-Goog-Upload-Command": "upload, finalize",
        "X-Goog-Upload-Header-Content-Type": mimeType,
        "Content-Type": mimeType,
        "X-Goog-Upload-Header-Content-Length": String(videoBuffer.length),
      },
      body: videoBuffer,
    }
  );

  if (!uploadRes.ok) {
    const err = await uploadRes.text();
    throw new Error(`Erro ao fazer upload para o Gemini: ${err}`);
  }

  const uploadData = await uploadRes.json();
  return { name: uploadData.file.name, uri: uploadData.file.uri };
}

async function waitForGeminiProcessing(fileName: string): Promise<string> {
  const maxAttempts = 30;
  let attempts = 0;

  while (attempts < maxAttempts) {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/${fileName}?key=${GEMINI_API_KEY}`
    );

    if (!res.ok) {
      throw new Error("Erro ao verificar status do arquivo no Gemini");
    }

    const data = await res.json();

    if (data.state !== "PROCESSING") {
      return data.uri;
    }

    await new Promise((resolve) => setTimeout(resolve, 3000));
    attempts++;
  }

  throw new Error("Timeout: arquivo não processado pelo Gemini a tempo");
}

async function analyzeWithGemini(fileUri: string, mimeType: string): Promise<string> {
  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [
          {
            parts: [
              { file_data: { mime_type: mimeType, file_uri: fileUri } },
              { text: ANALYSIS_PROMPT },
            ],
          },
        ],
        generationConfig: { temperature: 0.4, maxOutputTokens: 4096 },
      }),
    }
  );

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Erro na análise do Gemini: ${err}`);
  }

  const data = await res.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text || "";
}

async function transcribeWithWhisper(audioPath: string): Promise<string> {
  const openai = new OpenAI({ apiKey: OPENAI_API_KEY });

  const transcription = await openai.audio.transcriptions.create({
    file: createReadStream(audioPath) as Parameters<typeof openai.audio.transcriptions.create>[0]["file"],
    model: "whisper-1",
    language: "pt",
  });

  return transcription.text;
}

function getMimeType(filename: string): string {
  const ext = filename.toLowerCase().split(".").pop();
  switch (ext) {
    case "mp4":
      return "video/mp4";
    case "mov":
      return "video/quicktime";
    case "webm":
      return "video/webm";
    default:
      return "video/mp4";
  }
}

export async function POST(request: NextRequest) {
  const tmpFiles: string[] = [];

  try {
    const formData = await request.formData();
    const file = formData.get("video") as File | null;

    if (!file) {
      return NextResponse.json({ error: "Nenhum vídeo enviado" }, { status: 400 });
    }

    // Save video to /tmp
    const videoBytes = await file.arrayBuffer();
    const videoBuffer = Buffer.from(videoBytes);
    const videoFilename = `video_${Date.now()}_${file.name.replace(/[^a-zA-Z0-9._-]/g, "_")}`;
    const videoPath = join("/tmp", videoFilename);
    await writeFile(videoPath, videoBuffer);
    tmpFiles.push(videoPath);

    const mimeType = getMimeType(file.name);

    // Step 1: Transcribe audio with Whisper
    let transcription = "";
    const audioPath = join("/tmp", `audio_${Date.now()}.mp3`);
    tmpFiles.push(audioPath);

    try {
      await extractAudioWithFfmpeg(videoPath, audioPath);
      transcription = await transcribeWithWhisper(audioPath);
    } catch (err) {
      console.error("Erro na transcrição (continuando sem ela):", err);
      transcription = "[Transcrição não disponível]";
    }

    // Step 2: Upload video to Gemini File API
    const { name: fileName } = await uploadToGemini(videoPath, mimeType);

    // Step 3: Wait for Gemini to process
    const fileUri = await waitForGeminiProcessing(fileName);

    // Step 4: Analyze with Gemini
    const analysisText = await analyzeWithGemini(fileUri, mimeType);

    // Parse JSON from response
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

    return NextResponse.json({ transcription, analysis });
  } catch (error: unknown) {
    console.error("Erro na análise:", error);
    const message = error instanceof Error ? error.message : "Erro desconhecido";
    return NextResponse.json({ error: message }, { status: 500 });
  } finally {
    // Cleanup temp files
    for (const f of tmpFiles) {
      try {
        if (existsSync(f)) await unlink(f);
      } catch {
        // ignore cleanup errors
      }
    }
  }
}
