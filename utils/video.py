"""Wrappers finos sobre ffmpeg/ffprobe via subprocess.

Evita depender de moviepy/ffmpeg-python — o binário ffmpeg é chamado
diretamente e esperamos que esteja disponível no PATH.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


def _require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise FFmpegError(
            f"'{name}' não encontrado no PATH. Instale ffmpeg no servidor "
            "(nixpacks.toml já declara o pacote)."
        )
    return path


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise FFmpegError(
            f"Comando falhou: {' '.join(cmd[:3])}...\nstderr:\n{e.stderr[-2000:]}"
        ) from e
    return proc


def probe_duration(path: str) -> float:
    """Retorna duração do arquivo em segundos (float)."""
    _require_binary("ffprobe")
    proc = _run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        path,
    ])
    data = json.loads(proc.stdout or "{}")
    return float(data.get("format", {}).get("duration", 0.0))


def extract_audio(src_video: str, out_mp3: str, bitrate_kbps: int = 64) -> str:
    """Extrai áudio do vídeo como mp3 mono 16 kHz.

    ~28 MB/hora a 64 kbps — mantém cada chunk de 10 min bem abaixo do
    limite de 25 MB do Whisper API.
    """
    _require_binary("ffmpeg")
    Path(out_mp3).parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-y",
        "-i", src_video,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", f"{bitrate_kbps}k",
        "-f", "mp3",
        out_mp3,
    ])
    return out_mp3


def chunk_audio(src_mp3: str, out_dir: str, chunk_seconds: int = 600) -> list[dict]:
    """Divide o mp3 em pedaços de ~chunk_seconds segundos cada.

    Usa o muxer `segment` do ffmpeg. Cada pedaço é gravado como
    `chunk_000.mp3`, `chunk_001.mp3`, etc. Retorna a lista ordenada
    com metadados: ``[{"path": str, "start_offset": float, "duration": float}]``.
    """
    _require_binary("ffmpeg")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    pattern = str(out / "chunk_%03d.mp3")
    _run([
        "ffmpeg", "-y",
        "-i", src_mp3,
        "-f", "segment",
        "-segment_time", str(chunk_seconds),
        "-c", "copy",
        "-reset_timestamps", "1",
        pattern,
    ])

    chunks = sorted(out.glob("chunk_*.mp3"))
    if not chunks:
        raise FFmpegError("Nenhum chunk gerado pelo ffmpeg.")

    result = []
    offset = 0.0
    for p in chunks:
        dur = probe_duration(str(p))
        result.append({
            "path": str(p),
            "start_offset": offset,
            "duration": dur,
        })
        offset += dur
    return result


def cut_segment(src_video: str, out_mp4: str, start: float, end: float) -> str:
    """Corta [start, end] do vídeo e reencoda para garantir keyframe accuracy.

    Re-encode é obrigatório aqui: ``-c copy`` com ``-ss`` bate em
    keyframe mais próximo e produz cortes imprecisos para trechos
    curtos (clipes de 30–180 s). libx264 veryfast é rápido o bastante.
    """
    _require_binary("ffmpeg")
    Path(out_mp4).parent.mkdir(parents=True, exist_ok=True)

    if end <= start:
        raise ValueError(f"end ({end}) deve ser maior que start ({start})")

    _run([
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", src_video,
        "-to", f"{(end - start):.3f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        out_mp4,
    ])
    return out_mp4


def concat_segments(segment_paths: list[str], out_mp4: str) -> str:
    """Concatena mp4s gerados por ``cut_segment`` via concat demuxer.

    Como todos os cortes foram reencodados com os mesmos parâmetros,
    o concat demuxer funciona com ``-c copy`` (rápido, sem requalidade).
    """
    _require_binary("ffmpeg")
    if not segment_paths:
        raise ValueError("Nenhum segmento para concatenar.")

    Path(out_mp4).parent.mkdir(parents=True, exist_ok=True)
    list_path = Path(out_mp4).with_suffix(".concat.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in segment_paths:
            abs_path = os.path.abspath(p).replace("'", "'\\''")
            f.write(f"file '{abs_path}'\n")

    try:
        _run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_path),
            "-c", "copy",
            "-movflags", "+faststart",
            out_mp4,
        ])
    finally:
        try:
            list_path.unlink()
        except OSError:
            pass
    return out_mp4
