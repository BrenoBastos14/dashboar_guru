"""Segmentação do transcript em tópicos/clipes via LLM (OpenAI).

Passa os segments numerados e peça ao modelo para agrupar em capítulos
coerentes. Sempre validamos a saída e snapamos em bordas de segment
para nunca cortar no meio de uma frase.

Para vídeos longos (>150 segments ≈ >30min), o transcript é dividido
em chunks e processado por partes — evita estourar TPM e também ajuda
o modelo a não ser preguiçoso numa lista gigantesca.
"""

from __future__ import annotations

import json
import time
from typing import Callable, Optional

from openai import OpenAI


SEGMENTS_PER_CHUNK = 150  # ~30min de fala por chunk
SLEEP_BETWEEN_CHUNKS = 1.5  # folga pro TPM



SYSTEM_PROMPT = (
    "Você é um editor de vídeo que assiste à transcrição de uma aula, "
    "podcast ou palestra longa e identifica TODOS os trechos que podem virar "
    "clipes curtos independentes (highlights/shorts). "
    "Seja ABRANGENTE: extraia cada bloco temático distinto — afirmações "
    "fortes, insights, histórias, definições, exemplos, dicas práticas, "
    "perguntas respondidas, momentos com punch. "
    "NÃO limite a quantidade — em um vídeo de 1h pode haver 15-30 clipes; "
    "em 4h, 50-100 ou mais. Só ignore trechos vazios (só pausas, "
    "apresentação genérica, mero 'tchau'). "
    "Cada clipe é autocontido, começando e terminando em trechos existentes. "
    "Responda SEMPRE em JSON válido no formato: "
    '{"chapters": [{"title": "...", "summary": "...", '
    '"start_idx": N, "end_idx": M}]} '
    "onde start_idx e end_idx são os índices (0-based) dos trechos de "
    "abertura e fechamento. Os capítulos não podem se sobrepor e devem "
    "estar em ordem crescente. Não invente trechos que não existem."
)


def _mmss(sec: float) -> str:
    sec = max(0.0, float(sec))
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m:02d}:{s:02d}"


def _build_user_prompt(
    transcript: dict,
    min_clip_sec: int,
    max_clip_sec: int,
    target_n: Optional[int],
) -> str:
    segments = transcript.get("segments") or []
    lines = []
    for seg in segments:
        lines.append(
            f"[{seg['id']}] {_mmss(seg['start'])}-{_mmss(seg['end'])}: {seg['text']}"
        )
    guidance = (
        f"REGRAS OBRIGATÓRIAS:\n"
        f"- Cada clipe deve ter NO MÁXIMO {max_clip_sec}s (2 minutos).\n"
        f"- Cada clipe deve ter NO MÍNIMO {min_clip_sec}s.\n"
        f"- Selecione APENAS os trechos que ficariam bem como cortes "
        f"independentes — não precisa cobrir o vídeo inteiro.\n"
        f"- Gere quantos clipes forem relevantes; não há limite de quantidade.\n"
    )
    if target_n:
        guidance += f"- Tente produzir cerca de {target_n} clipes.\n"
    guidance += (
        "- Títulos curtos (até 8 palavras), chamativos.\n"
        "- Summary de 1 frase explicando o porquê do corte."
    )
    return guidance + "\n\nTranscrição:\n" + "\n".join(lines)


def _parse_chapters(raw: str) -> list[dict]:
    data = json.loads(raw)
    chapters = data.get("chapters") if isinstance(data, dict) else None
    if not isinstance(chapters, list):
        raise ValueError("Resposta sem chave 'chapters' válida.")
    return chapters


def _snap_to_segments(
    chapters: list[dict],
    segments: list[dict],
    duration: float,
    min_clip_sec: int,
) -> list[dict]:
    """Valida, clampa e mapeia start_idx/end_idx para timestamps reais."""
    result = []
    seen_end = -1
    for ch in chapters:
        try:
            start_idx = int(ch.get("start_idx"))
            end_idx = int(ch.get("end_idx"))
        except (TypeError, ValueError):
            continue

        if start_idx < 0 or end_idx >= len(segments) or end_idx < start_idx:
            continue
        if start_idx <= seen_end:
            # Evita sobreposições — LLM às vezes repete índices.
            start_idx = seen_end + 1
            if start_idx > end_idx:
                continue

        start = float(segments[start_idx]["start"])
        end = float(segments[end_idx]["end"])
        start = max(0.0, start)
        end = min(duration, end)

        if end - start < min_clip_sec:
            continue

        title = (ch.get("title") or "").strip() or f"Clipe {len(result) + 1}"
        summary = (ch.get("summary") or "").strip()

        result.append({
            "title": title,
            "summary": summary,
            "start": start,
            "end": end,
            "segment_indices": list(range(start_idx, end_idx + 1)),
        })
        seen_end = end_idx
    return result


def _process_chunk(
    client: OpenAI,
    model: str,
    chunk_segments: list[dict],
    offset: int,
    min_clip_sec: int,
    max_clip_sec: int,
    target_n: Optional[int],
) -> list[dict]:
    """Processa um chunk de segments. Reindexa pra 0-based localmente e
    adiciona offset nos índices retornados pra bater com a lista original."""
    local = [{**s, "id": j} for j, s in enumerate(chunk_segments)]
    local_duration = float(chunk_segments[-1]["end"])
    local_transcript = {"segments": local, "duration": local_duration}
    user_prompt = _build_user_prompt(local_transcript, min_clip_sec, max_clip_sec, target_n)

    def _ask(extra_system: str = "") -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + extra_system},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=8192,
        )
        return resp.choices[0].message.content or "{}"

    try:
        chapters = _parse_chapters(_ask())
    except (json.JSONDecodeError, ValueError):
        chapters = _parse_chapters(_ask(
            " Sua resposta anterior não foi JSON válido. "
            "Responda APENAS o objeto JSON pedido, sem texto extra."
        ))

    # Offset pros índices globais.
    for ch in chapters:
        try:
            ch["start_idx"] = int(ch.get("start_idx")) + offset
            ch["end_idx"] = int(ch.get("end_idx")) + offset
        except (TypeError, ValueError):
            pass
    return chapters


def segment_topics(
    transcript: dict,
    api_key: str,
    min_clip_sec: int = 30,
    max_clip_sec: int = 180,
    target_n: Optional[int] = None,
    model: str = "gpt-4o-mini",
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> list[dict]:
    """Chama o LLM (em chunks, se necessário) e retorna tópicos validados."""
    segments = transcript.get("segments") or []
    if not segments:
        return []

    duration = float(transcript.get("duration") or segments[-1]["end"])
    client = OpenAI(api_key=api_key)

    all_chapters: list[dict] = []
    total_chunks = max(1, (len(segments) + SEGMENTS_PER_CHUNK - 1) // SEGMENTS_PER_CHUNK)

    for i in range(total_chunks):
        start = i * SEGMENTS_PER_CHUNK
        end = min(len(segments), start + SEGMENTS_PER_CHUNK)
        chunk = segments[start:end]
        if not chunk:
            continue
        if progress_cb:
            progress_cb(i, total_chunks)
        chapters = _process_chunk(
            client, model, chunk, start,
            min_clip_sec, max_clip_sec, target_n,
        )
        all_chapters.extend(chapters)
        if i < total_chunks - 1:
            time.sleep(SLEEP_BETWEEN_CHUNKS)

    if progress_cb:
        progress_cb(total_chunks, total_chunks)

    return _snap_to_segments(all_chapters, segments, duration, min_clip_sec)
