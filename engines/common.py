# -*- coding: utf-8 -*-
"""通用工具：图像加载 / 归一化 / 设备选择。"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# 设备选择 (Apple Silicon MPS / CPU)
# ---------------------------------------------------------------------------

def pick_device() -> str:
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def load_image(path: str) -> Image.Image:
    img = Image.open(path)
    img.load()
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    return img


def to_rgb_array(img: Image.Image) -> np.ndarray:
    """转 RGB uint8 ndarray (H,W,3)。"""
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.asarray(img, dtype=np.uint8)


def resize_keep_aspect(img: Image.Image, max_side: int) -> Image.Image:
    """等比缩放到最长边 = max_side。"""
    w, h = img.size
    longer = max(w, h)
    if longer <= max_side:
        return img
    scale = max_side / float(longer)
    return img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)


def alpha_to_png_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    import io
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)
    return p
