"""Renderiza clipes individuais, concatena o vídeo final e empacota tudo em zip."""

from __future__ import annotations

import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Callable, Optional

from .video import concat_segments, cut_segment


def _slugify(text: str, max_len: int = 40) -> str:
    norm = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    norm = norm.lower()
    norm = re.sub(r"[^a-z0-9]+", "_", norm).strip("_")
    return (norm or "clipe")[:max_len]


def render_clips(
    src_video: str,
    topics: list[dict],
    out_dir: str,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """Gera um mp4 por tópico + um ``final.mp4`` concatenado.

    Retorna ``{"clips": [path, ...], "final": path}``.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    clip_paths: list[str] = []
    total = len(topics)
    for i, topic in enumerate(topics):
        if progress_cb:
            progress_cb(i, total)
        slug = _slugify(topic.get("title") or f"clipe_{i+1}")
        clip_path = out / f"clip_{i+1:02d}_{slug}.mp4"
        cut_segment(src_video, str(clip_path), topic["start"], topic["end"])
        clip_paths.append(str(clip_path))

    if progress_cb:
        progress_cb(total, total)

    final_path = out / "final.mp4"
    if clip_paths:
        concat_segments(clip_paths, str(final_path))

    return {"clips": clip_paths, "final": str(final_path) if clip_paths else ""}


def build_output_zip(
    zip_path: str,
    clip_paths: list[str],
    final_path: str,
    srt_text: str,
    vtt_text: str,
    chapters_json: str,
) -> str:
    """Empacota todas as saídas em um único zip."""
    Path(zip_path).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if final_path and Path(final_path).exists():
            zf.write(final_path, arcname="final.mp4")
        for p in clip_paths:
            if Path(p).exists():
                zf.write(p, arcname=f"clips/{Path(p).name}")
        zf.writestr("transcript.srt", srt_text)
        zf.writestr("transcript.vtt", vtt_text)
        zf.writestr("chapters.json", chapters_json)
    return zip_path
