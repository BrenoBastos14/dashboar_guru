"""Transcrição via OpenAI Whisper API + stitch + exportação SRT/VTT.

Cada chunk é enviado individualmente e os timestamps recebidos são
deslocados pelo ``start_offset`` do chunk, produzindo um transcript
global com timings corretos no vídeo original.
"""

from __future__ import annotations

from typing import Callable, Optional

from openai import OpenAI


TranscriptCallback = Optional[Callable[[int, int], None]]


def _client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def transcribe_chunk(mp3_path: str, api_key: str, language: Optional[str] = None) -> dict:
    """Chama Whisper API em um arquivo de áudio.

    Retorna dict com ``segments`` (cada um com ``start``, ``end``,
    ``text``) e opcionalmente ``words``. Usa ``verbose_json`` para
    receber timestamps.
    """
    client = _client(api_key)
    kwargs = {
        "model": "whisper-1",
        "response_format": "verbose_json",
        "timestamp_granularities": ["segment", "word"],
    }
    if language and language != "auto":
        kwargs["language"] = language

    with open(mp3_path, "rb") as f:
        resp = client.audio.transcriptions.create(file=f, **kwargs)

    # SDK devolve um objeto Pydantic; convertemos para dict plano.
    if hasattr(resp, "model_dump"):
        return resp.model_dump()
    return dict(resp)


def transcribe_all(
    chunks: list[dict],
    api_key: str,
    language: Optional[str] = None,
    progress_cb: TranscriptCallback = None,
) -> dict:
    """Transcreve todos os chunks e stitch dos timestamps.

    Retorna transcript global:
    ``{"language": str, "duration": float, "segments": [...]}``
    onde cada segment tem ``id``, ``start``, ``end``, ``text``, ``words``.
    """
    all_segments: list[dict] = []
    detected_language: Optional[str] = None
    total_duration = 0.0
    seg_id = 0

    for i, chunk in enumerate(chunks):
        if progress_cb:
            progress_cb(i, len(chunks))
        raw = transcribe_chunk(chunk["path"], api_key, language=language)
        offset = float(chunk["start_offset"])
        detected_language = detected_language or raw.get("language")
        total_duration = max(total_duration, offset + float(chunk.get("duration", 0.0)))

        for seg in raw.get("segments") or []:
            start = float(seg.get("start", 0.0)) + offset
            end = float(seg.get("end", start)) + offset
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            # Filtra duplicatas nas bordas entre chunks (segurança).
            if all_segments:
                prev = all_segments[-1]
                if abs(prev["start"] - start) < 0.5 and prev["text"] == text:
                    continue
            words_out = []
            for w in seg.get("words") or []:
                words_out.append({
                    "start": float(w.get("start", 0.0)) + offset,
                    "end": float(w.get("end", 0.0)) + offset,
                    "word": w.get("word") or w.get("text") or "",
                })
            all_segments.append({
                "id": seg_id,
                "start": start,
                "end": end,
                "text": text,
                "words": words_out,
            })
            seg_id += 1

        # Palavras soltas (quando vêm no topo, fora de segments).
        # Não quebramos se a API mudar a forma — segments já são a
        # fonte primária para corte.

    if progress_cb:
        progress_cb(len(chunks), len(chunks))

    return {
        "language": detected_language or language or "auto",
        "duration": total_duration,
        "segments": all_segments,
    }


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def _fmt_time_srt(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _fmt_time_vtt(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def transcript_to_srt(transcript: dict) -> str:
    lines = []
    for i, seg in enumerate(transcript.get("segments") or [], start=1):
        lines.append(str(i))
        lines.append(f"{_fmt_time_srt(seg['start'])} --> {_fmt_time_srt(seg['end'])}")
        lines.append(seg["text"].strip())
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def transcript_to_vtt(transcript: dict) -> str:
    lines = ["WEBVTT", ""]
    for seg in transcript.get("segments") or []:
        lines.append(f"{_fmt_time_vtt(seg['start'])} --> {_fmt_time_vtt(seg['end'])}")
        lines.append(seg["text"].strip())
        lines.append("")
    return "\n".join(lines).strip() + "\n"
