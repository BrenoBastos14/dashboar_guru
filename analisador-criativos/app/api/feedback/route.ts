import { NextRequest, NextResponse } from "next/server";
import { readFile, writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { existsSync } from "fs";

// On Vercel, use /tmp (ephemeral). Locally, use data/ folder (persistent).
const DATA_DIR = process.env.VERCEL ? "/tmp" : join(process.cwd(), "data");
const DB_PATH = join(DATA_DIR, "feedback.json");

export interface FeedbackEntry {
  id: string;
  date: string;
  videoName: string;
  notaGemini: number;
  formato: string;
  resultado: string; // "Escalou" | "Bom" | "Médio" | "Ruim" | "Morreu rápido"
  gasto: string;
  roas: string;
  observacoes: string;
  hookAvaliacao: string;
  ctaAvaliacao: string;
}

async function readDB(): Promise<FeedbackEntry[]> {
  try {
    if (!existsSync(DB_PATH)) return [];
    const raw = await readFile(DB_PATH, "utf-8");
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

async function writeDB(entries: FeedbackEntry[]): Promise<void> {
  if (!existsSync(DATA_DIR)) {
    await mkdir(DATA_DIR, { recursive: true });
  }
  await writeFile(DB_PATH, JSON.stringify(entries, null, 2), "utf-8");
}

export async function GET() {
  const entries = await readDB();
  return NextResponse.json(entries);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const entries = await readDB();

    const newEntry: FeedbackEntry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      date: new Date().toISOString(),
      videoName: body.videoName || "Sem nome",
      notaGemini: body.notaGemini || 0,
      formato: body.formato || "",
      resultado: body.resultado || "",
      gasto: body.gasto || "",
      roas: body.roas || "",
      observacoes: body.observacoes || "",
      hookAvaliacao: body.hookAvaliacao || "",
      ctaAvaliacao: body.ctaAvaliacao || "",
    };

    entries.unshift(newEntry); // newest first
    await writeDB(entries);

    return NextResponse.json({ ok: true, entry: newEntry });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Erro ao salvar";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { id } = await request.json();
    const entries = await readDB();
    const filtered = entries.filter((e) => e.id !== id);
    await writeDB(filtered);
    return NextResponse.json({ ok: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Erro ao deletar";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
