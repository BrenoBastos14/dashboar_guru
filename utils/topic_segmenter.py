"""Segmentação do transcript em tópicos/clipes via LLM (OpenAI).

Passa os segments numerados e peça ao modelo para agrupar em capítulos
coerentes. Sempre validamos a saída e snapamos em bordas de segment
para nunca cortar no meio de uma frase.
"""

from __future__ import annotations

import json
from typing import Optional

from openai import OpenAI


SYSTEM_PROMPT = (
    "Você é um editor de vídeo sênior que assiste à transcrição de uma aula, "
    "podcast ou palestra longa e SELECIONA apenas os melhores momentos para "
    "virar clipes curtos e impactantes (highlights/shorts). "
    "Seja criterioso: escolha somente trechos que funcionam sozinhos — "
    "afirmações fortes, insights, histórias completas, momentos com punch. "
    "IGNORE: introduções genéricas, digressões, repetições, trechos sem "
    "contexto ou sem payoff. Prefira qualidade sobre quantidade. "
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


def segment_topics(
    transcript: dict,
    api_key: str,
    min_clip_sec: int = 30,
    max_clip_sec: int = 180,
    target_n: Optional[int] = None,
    model: str = "gpt-4o-mini",
) -> list[dict]:
    """Chama o LLM e retorna a lista de tópicos validada."""
    segments = transcript.get("segments") or []
    if not segments:
        return []

    duration = float(transcript.get("duration") or segments[-1]["end"])
    user_prompt = _build_user_prompt(transcript, min_clip_sec, max_clip_sec, target_n)

    client = OpenAI(api_key=api_key)

    def _ask(extra_system: str = "") -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + extra_system},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return resp.choices[0].message.content or "{}"

    try:
        chapters = _parse_chapters(_ask())
    except (json.JSONDecodeError, ValueError):
        # Um retry com instrução mais explícita.
        chapters = _parse_chapters(_ask(
            " Sua resposta anterior não foi JSON válido. "
            "Responda APENAS o objeto JSON pedido, sem texto extra."
        ))

    return _snap_to_segments(chapters, segments, duration, min_clip_sec)
