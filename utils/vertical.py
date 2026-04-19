"""Conversão de clipes horizontais (16:9) em vertical 9:16 para reels/shorts.

Detecta o rosto com o cascade Haar do OpenCV (tira uma média de amostras no
clipe), decide o layout e compõe o output 1080x1920 via filtros ffmpeg:
- side_by_side: top = metade com a face; bottom = metade com os slides
- pip: top = crop quadrado ao redor da face; bottom = frame inteiro
- face_only: crop vertical 9:16 centrado na face
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Literal, Optional

import cv2
import numpy as np


OUT_W = 1080
OUT_H = 1920
HALF_H = OUT_H // 2  # 960
# side_by_side usa 30/70: apresentação em cima, pessoa grande embaixo.
SBS_TOP_H = 576
SBS_BOT_H = OUT_H - SBS_TOP_H  # 1344

Layout = Literal["auto", "side_by_side", "pip", "face_only"]


def _detect_face_average(video_path: str, samples: int = 20) -> Optional[tuple[float, float, float, float]]:
    """Amostra ~N frames e devolve o rosto médio em coords relativas [0,1].

    Retorna (cx, cy, w, h) ou None se nenhum rosto foi detectado.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release()
        return None

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)

    step = max(1, total // samples)
    centers: list[tuple[float, float]] = []
    sizes: list[tuple[float, float]] = []
    try:
        frame_idx = 0
        while frame_idx < total and len(centers) < samples:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape[:2]
            faces = detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )
            if len(faces) > 0:
                x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                centers.append(((x + fw / 2) / w, (y + fh / 2) / h))
                sizes.append((fw / w, fh / h))
            frame_idx += step
    finally:
        cap.release()

    if not centers:
        return None
    cx = float(np.mean([c[0] for c in centers]))
    cy = float(np.mean([c[1] for c in centers]))
    bw = float(np.mean([s[0] for s in sizes]))
    bh = float(np.mean([s[1] for s in sizes]))
    return (cx, cy, bw, bh)


def _probe_size(video_path: str) -> tuple[int, int]:
    cap = cv2.VideoCapture(video_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return w, h


def _even(n: int) -> int:
    return n - (n % 2)


def _auto_layout(face: Optional[tuple[float, float, float, float]]) -> Layout:
    if face is None:
        return "face_only"
    _, _, fw, _ = face
    fx = face[0]
    # Face pequena (< 15% da largura) → provavelmente PiP
    if fw < 0.15:
        return "pip"
    # Face deslocada pra um dos lados → side_by_side
    if abs(fx - 0.5) > 0.12:
        return "side_by_side"
    return "face_only"


def _run_ffmpeg(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ffmpeg falhou: {' '.join(cmd[:3])}...\nstderr:\n{e.stderr[-1500:]}"
        ) from e


def _render_side_by_side(src: str, out: str, face, sw: int, sh: int) -> str:
    # Bottom: crop apertado em torno do rosto, aspect OUT_W:SBS_BOT_H.
    bot_ar = OUT_W / SBS_BOT_H
    if face:
        fcx = face[0] * sw
        fcy = face[1] * sh
        fh_px = max(1.0, face[3] * sh)
        # Rosto ocupa ~40% da altura do quadro final.
        crop_h = int(fh_px / 0.40)
        crop_w = int(crop_h * bot_ar)
        crop_h = min(crop_h, sh)
        crop_w = min(crop_w, sw)
        if crop_w / max(1, crop_h) > bot_ar:
            crop_w = int(crop_h * bot_ar)
        else:
            crop_h = int(crop_w / bot_ar)
        crop_w = _even(max(240, crop_w))
        crop_h = _even(max(240, crop_h))
        x0 = _even(int(max(0, min(sw - crop_w, fcx - crop_w / 2))))
        y0 = _even(int(max(0, min(sh - crop_h, fcy - crop_h / 2))))
    else:
        crop_h = sh
        crop_w = _even(min(sw, int(sh * bot_ar)))
        x0 = _even(int((sw - crop_w) / 2))
        y0 = 0

    # Top: separa a parte do rosto da parte do conteúdo.
    # Usa a posição do rosto pra decidir qual lado do frame é slide/apresentação.
    if face:
        fx = face[0]
        fw = face[2]
        if fw < 0.15:
            # Rosto pequeno (PiP no canto) → margem generosa.
            margin = fw * 4.0 + 0.05
        else:
            # Rosto grande (native split) → corta rente à borda do rosto.
            margin = fw * 0.7 + 0.02
        if fx < 0.5:
            cut_at = max(0.35, min(0.55, fx + margin))
            top_cx = _even(int(sw * cut_at))
            top_cw = _even(sw - top_cx)
        else:
            cut_at = max(0.45, min(0.65, fx - margin))
            top_cx = 0
            top_cw = _even(int(sw * cut_at))
        top_pre = f"crop={top_cw}:{sh}:{top_cx}:0,"
    else:
        top_pre = ""

    filter_complex = (
        f"[0:v]{top_pre}"
        f"scale={OUT_W}:{SBS_TOP_H}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={OUT_W}:{SBS_TOP_H}[top];"
        f"[0:v]crop={crop_w}:{crop_h}:{x0}:{y0},"
        f"scale={OUT_W}:{SBS_BOT_H}:flags=lanczos[bottom];"
        f"[top][bottom]vstack=inputs=2[out]"
    )
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", src,
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        out,
    ])
    return out


def _render_pip(src: str, out: str, face, sw: int, sh: int) -> str:
    if face is None:
        return _render_face_only(src, out, face, sw, sh)
    fcx = face[0] * sw
    fcy = face[1] * sh
    # Expand ~2x a bbox para dar respiro, quadrado.
    side = int(max(face[2] * sw, face[3] * sh) * 2.2)
    side = max(side, 240)
    side = min(side, min(sw, sh))
    side = _even(side)
    x0 = _even(int(max(0, min(sw - side, fcx - side / 2))))
    y0 = _even(int(max(0, min(sh - side, fcy - side / 2))))

    filter_complex = (
        f"[0:v]crop={side}:{side}:{x0}:{y0},"
        f"scale=1080:960:flags=lanczos[top];"
        f"[0:v]scale=1080:-2:flags=lanczos,"
        f"pad=1080:960:0:(960-ih)/2:color=black,crop=1080:960[bottom];"
        f"[top][bottom]vstack=inputs=2[out]"
    )
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", src,
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        out,
    ])
    return out


def _render_face_only(src: str, out: str, face, sw: int, sh: int) -> str:
    # Corta vertical 9:16 do source.
    crop_w = _even(int(sh * 9 / 16))
    crop_w = min(crop_w, sw)
    fcx = (face[0] * sw) if face else (sw / 2)
    x0 = _even(int(max(0, min(sw - crop_w, fcx - crop_w / 2))))

    filter_complex = (
        f"[0:v]crop={crop_w}:{sh}:{x0}:0,"
        f"scale=1080:1920:flags=lanczos[out]"
    )
    _run_ffmpeg([
        "ffmpeg", "-y", "-i", src,
        "-filter_complex", filter_complex,
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        out,
    ])
    return out


def render_vertical(
    src_clip: str,
    out_path: str,
    layout: Layout = "auto",
) -> tuple[str, Layout]:
    """Renderiza 1080x1920 de um clipe 16:9. Retorna (path, layout_usado)."""
    src_clip = str(src_clip)
    out_path = str(out_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    sw, sh = _probe_size(src_clip)
    if sw == 0 or sh == 0:
        raise RuntimeError(f"Não consegui ler dimensões de {src_clip}")

    face = _detect_face_average(src_clip)
    chosen = _auto_layout(face) if layout == "auto" else layout

    if chosen == "side_by_side":
        _render_side_by_side(src_clip, out_path, face, sw, sh)
    elif chosen == "pip":
        _render_pip(src_clip, out_path, face, sw, sh)
    else:
        _render_face_only(src_clip, out_path, face, sw, sh)

    return out_path, chosen


def render_vertical_batch(
    clip_paths: list[str],
    out_dir: str,
    layout: Layout = "auto",
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> list[dict]:
    """Processa vários clipes. Retorna lista de {path, layout, source}."""
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)
    results = []
    total = len(clip_paths)
    for i, src in enumerate(clip_paths):
        if progress_cb:
            progress_cb(i, total)
        name = Path(src).stem + "_vertical.mp4"
        out = out_dir_p / name
        try:
            path, used = render_vertical(src, str(out), layout)
            results.append({"path": path, "layout": used, "source": src})
        except Exception as e:
            results.append({"path": None, "layout": layout, "source": src, "error": str(e)})
    if progress_cb:
        progress_cb(total, total)
    return results
