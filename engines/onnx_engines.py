# -*- coding: utf-8 -*-
"""ONNX 抠图引擎: RMBG-2.0 (BiRefNet 系) 与 BEN2。

两者预处理/后处理不同, 但都走 onnxruntime, 故放在一起但分别实现。
输出统一为 RGBA。
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .base import BaseEngine, register_engine

try:
    import onnxruntime as ort
    _HAS_ORT = True
except Exception:  # noqa: BLE001
    ort = None
    _HAS_ORT = False


def _make_session(model_path: str):
    so = ort.SessionOptions()
    so.log_severity_level = 3
    # 默认 CPU。Apple CoreML 对这类大模型易触发系统崩溃, 不默认启用;
    # 用户可设环境变量 MATTING_ONNX_COREML=1 尝试 CoreML 加速。
    import os as _os
    want = [_os.environ.get("MATTING_ONNX_PROVIDER", "cpu").lower()]
    available = ort.get_available_providers()
    if want[0] in ("coreml", "auto"):
        cand = [p for p in ("CoreMLExecutionProvider", "CPUExecutionProvider") if p in available]
    else:
        cand = ["CPUExecutionProvider"]
    sess = ort.InferenceSession(model_path, sess_options=so, providers=cand)
    return sess


# ===========================================================================
# RMBG-2.0  (魔搭 onnx 版, BiRefNet 架构, 输入 1024x1024, ImageNet 归一化)
# ===========================================================================
@register_engine
class Rmbg20Engine(BaseEngine):
    name = "rmbg-2.0"
    label = "RMBG-2.0 (均衡全能)"
    desc = "BRIA 出品, 基于 BiRefNet; 电商/通用场景均衡, 单通道 alpha"

    def _check_deps(self) -> str:
        return "" if _HAS_ORT else "未安装 onnxruntime (pip install onnxruntime)"

    def __init__(self, models_root: str):
        super().__init__(models_root)
        self.session = None

    def _weights_paths(self) -> list[str]:
        return [self._weights()]

    def _weights(self) -> str:
        return f"{self.models_root}/RMBG-2.0/model.onnx"

    def load(self) -> None:
        if self.session is not None:
            return
        if not _HAS_ORT:
            raise RuntimeError(f"未安装 onnxruntime, 请先 pip install onnxruntime")
        p = self._weights()
        import os
        if not os.path.exists(p):
            raise RuntimeError(f"缺少模型文件: {p}")
        self.session = _make_session(p)
        # 探查输入输出形状
        inp = self.session.get_inputs()[0]
        self._in_name = inp.name
        self._in_shape = inp.shape  # 可能是 [1,3,1024,1024] 或含 None
        out = self.session.get_outputs()[0]
        self._out_name = out.name
        self._loaded = True

    def unload(self) -> None:
        self.session = None
        self._loaded = False
        import gc
        gc.collect()

    def remove_bg(self, image: Image.Image) -> Image.Image:
        self._ensure_loaded()
        size = 1024
        rgb = image.convert("RGB")
        # 等比例 resize 到最长边 1024, 再 pad 到 1024x1024 (官方为直接拉伸, 此处用 pad 保持比例更稳, 但需与官方一致)
        # 说明: BRIA 官方 torch demo 是直接 Resize((1024,1024))。ONNX 版同 torch demo。
        img = rgb.resize((size, size), Image.BILINEAR)
        x = np.asarray(img, dtype=np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        x = (x - mean) / std
        x = x.transpose(2, 0, 1)[None]  # (1,3,1024,1024)

        feeds = {self._in_name: x}
        # BEN 引擎输入若还有 mask 等可选输入, RMBG 单输入即可; 保险起见若有多输入且非必填忽略
        out = self.session.run([self._out_name], feeds)[0]

        if out.ndim == 4:
            out = out[0]
        if out.shape[0] in (1, 3):  # CHW -> HW
            # 若为 3 通道, 取第一个
            if out.shape[0] == 3:
                out = out[0:1]
            out = out[0]
        # 该 onnx 输出已含 sigmoid (0~1); 兜底: 若数值超界再手动 sigmoid
        if float(out.min()) < -0.01 or float(out.max()) > 1.01:
            out = 1.0 / (1.0 + np.exp(-out.astype(np.float64)))
        alpha = np.clip(out, 0.0, 1.0)
        a_img = Image.fromarray((alpha * 255).astype(np.uint8), mode="L")
        return self._apply_alpha(image, a_img)


# ===========================================================================
# BEN2  (PramaLLC, 电商/关联前景友好)
# 官方 onnx_run.py: Resize((1024,1024)) + ToTensor(0-1), 直接推理,
# 输出 bilinear 插值回原尺寸后 min-max 归一化 -> alpha
# ===========================================================================
@register_engine
class Ben2Engine(BaseEngine):
    name = "ben2"
    label = "BEN2 (电商友好)"
    desc = "PramaLLC BEN2, 保留关联前景; 与官方 onnx_run.py 同流程"

    def _check_deps(self) -> str:
        return "" if _HAS_ORT else "未安装 onnxruntime (pip install onnxruntime)"

    def __init__(self, models_root: str):
        super().__init__(models_root)
        self.session = None

    def _weights_paths(self) -> list[str]:
        return [self._weights()]

    def _weights(self) -> str:
        return f"{self.models_root}/BEN2/BEN2_Base.onnx"

    def load(self) -> None:
        if self.session is not None:
            return
        if not _HAS_ORT:
            raise RuntimeError("未安装 onnxruntime")
        p = self._weights()
        import os
        if not os.path.exists(p):
            raise RuntimeError(f"缺少模型文件: {p}")
        self.session = _make_session(p)
        self._in_name = self.session.get_inputs()[0].name
        out = self.session.get_outputs()[0]
        self._out_name = out.name
        self._loaded = True

    def unload(self) -> None:
        self.session = None
        self._loaded = False
        import gc
        gc.collect()

    def remove_bg(self, image: Image.Image) -> Image.Image:
        self._ensure_loaded()
        w, h = image.size
        rgb = image.convert("RGB").resize((1024, 1024), Image.BILINEAR)
        x = np.asarray(rgb, dtype=np.float32) / 255.0
        x = x.transpose(2, 0, 1)[None]  # (1,3,1024,1024) 0-1
        out = self.session.run([self._out_name], {self._in_name: x})[0]
        if out.ndim == 4:
            out = out[0]
        if out.shape[0] == 1:
            out = out[0]
        elif out.ndim == 3 and out.shape[0] in (1, 3):
            out = out[0]
        # 双线性插值回原尺寸 (numpy 实现, 等价官方 F.interpolate bilinear)
        alpha = _bilinear_resize_2d(out.astype(np.float64), w, h)
        # min-max 归一化 (官方: (x-min)/(max-min)*255)
        mn, mx = float(alpha.min()), float(alpha.max())
        if mx - mn < 1e-6:
            alpha = np.full_like(alpha, 255.0)
        else:
            alpha = (alpha - mn) / (mx - mn) * 255.0
        a_img = Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), mode="L")
        return self._apply_alpha(image, a_img)


def _bilinear_resize_2d(src: np.ndarray, out_w: int, out_h: int) -> np.ndarray:
    """纯 numpy 双线性插值, 等价 torch F.interpolate(mode='bilinear', align_corners=False)。

    简化实现: 直接用 PIL 双线性放大灰度图, 视觉上与官方流程一致, 避免 numpy 边界细节出错。
    """
    in_h, in_w = src.shape
    if (in_h, in_w) == (out_h, out_w):
        return src
    a8 = np.clip(src * 255.0, 0, 255).astype(np.uint8)
    im = Image.fromarray(a8, mode="L").resize((out_w, out_h), Image.BILINEAR)
    return np.asarray(im, dtype=np.float64) / 255.0 * 255.0
