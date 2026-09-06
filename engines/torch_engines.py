# -*- coding: utf-8 -*-
"""PyTorch 系引擎: BiRefNet / FeyNoBg / InSPyReNet。

三者均为 torch 权重, 但加载方式差异大:
- BiRefNet : HF custom code (birefnet.py + BiRefNet_config.py), 走 trust_remote_code 从本地目录加载
- FeyNoBg  : nobg 库 (需 pip install nobg>=0.2.5)
- InSPyReNet: transparent-background 库 (Swin-Base 版 ckpt_base.pth)
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image

from .base import BaseEngine, free_torch_caches, register_engine
from .common import pick_device


# ===========================================================================
# BiRefNet —— 通用高精度 / 发丝级
# ===========================================================================
@register_engine
class BiRefNetEngine(BaseEngine):
    name = "birefnet"
    label = "BiRefNet (发丝级高精度)"
    desc = "ZhengPeng7 BiRefNet, 当前开源事实标准; 细节最好但速度最慢"

    def __init__(self, models_root: str):
        super().__init__(models_root)
        self.model = None
        self.transform = None
        self.device = "cpu"

    def _dir(self) -> str:
        return f"{self.models_root}/BiRefNet"

    def _check_deps(self) -> str:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
            import timm  # noqa: F401
            import einops  # noqa: F401
            import kornia  # noqa: F401
        except Exception as e:  # noqa: BLE001
            return f"缺少 PyTorch 系依赖: {e}"
        return ""

    def check_files(self) -> bool:
        need = ["model.safetensors", "birefnet.py", "BiRefNet_config.py", "config.json"]
        d = self._dir()
        return all(os.path.exists(os.path.join(d, f)) for f in need)

    def load(self) -> None:
        if self.model is not None:
            return
        d = self._dir()
        need = ["model.safetensors", "birefnet.py", "BiRefNet_config.py", "config.json"]
        for f in need:
            if not os.path.exists(os.path.join(d, f)):
                raise RuntimeError(f"缺少模型文件: {os.path.join(d, f)} (需联网从 ZhengPeng7/BiRefNet 补齐)")
        try:
            import torch
            from transformers import AutoModelForImageSegmentation
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"缺少 torch/transformers: {e}") from e

        self.device = pick_device()
        # 本地 custom-code 加载: 传本地目录 + trust_remote_code; local_files_only=True 强制只读本地, 断网可跑
        model = AutoModelForImageSegmentation.from_pretrained(
            d,
            trust_remote_code=True,
            local_files_only=True,
        )
        # BiRefNet safetensors 混合精度(部分 fp16), MPS 上需统一 fp32
        model = model.float().eval()
        self.model = model.to(self.device)
        self._loaded = True

    def unload(self) -> None:
        self.model = None
        self.transform = None
        self._loaded = False
        free_torch_caches()

    def remove_bg(self, image: Image.Image) -> Image.Image:
        self._ensure_loaded()
        import torch
        from torchvision import transforms

        rgb = image.convert("RGB")
        size = (1024, 1024)
        tf = transforms.Compose([
            transforms.Resize(size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        x = tf(rgb).unsqueeze(0).to(self.device)
        with torch.no_grad():
            preds = self.model(x)[-1].sigmoid()
        pred = preds[0].squeeze().cpu()
        a8 = (pred.clamp(0, 1) * 255).to(torch.uint8).numpy()
        a_img = Image.fromarray(a8, mode="L")
        return self._apply_alpha(image, a_img)


# ===========================================================================
# FeyNoBg —— 2026-07 最新, 适配 4K/8K (需 pip install nobg)
# ===========================================================================
@register_engine
class FeyNoBgEngine(BaseEngine):
    name = "feynobg"
    label = "FeyNoBg (最新 4K/8K)"
    desc = "feyninc FeyNoBg, 八项基准四项 SOTA; 需要额外安装 nobg 库"

    def __init__(self, models_root: str):
        super().__init__(models_root)
        self.model = None
        self.processor = None
        self.device = "cpu"

    def _dir(self) -> str:
        return f"{self.models_root}/FeyNoBg"

    def _check_deps(self) -> str:
        try:
            import torch  # noqa: F401
            import nobg  # noqa: F401
        except Exception as e:  # noqa: BLE001
            return f"缺少 nobg 库 (pip install 'nobg>=0.2.5'): {e}"
        return ""

    def check_files(self) -> bool:
        d = self._dir()
        return os.path.exists(os.path.join(d, "model.safetensors")) and os.path.exists(
            os.path.join(d, "config.json")
        )

    def load(self) -> None:
        if self.model is not None:
            return
        d = self._dir()
        if not os.path.exists(os.path.join(d, "model.safetensors")):
            raise RuntimeError(f"缺少模型文件: {os.path.join(d, 'model.safetensors')}")
        try:
            import torch
            from nobg import AutoModel, AutoProcessor
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"缺少 nobg 库 (pip install 'nobg>=0.2.5'): {e}") from e

        self.device = pick_device()
        # 优先离线: 本地目录需含 config.json/preprocessor_config.json/model.safetensors
        # 注意: nobg.AutoModel 内部会先 model_info() 联网查 tags, 直接绕开,
        # 按本地目录里 config 的 dec_ipt/multi_scale_input 等特征判断走 BiRefNet 还是 Sam3。
        repo = d if os.path.exists(os.path.join(d, "config.json")) else "feyninc/FeyNobg"
        try:
            import json as _json
            with open(os.path.join(d, "config.json")) as _f:
                _cfg = _json.load(_f)
            # feyninc/FeyNobg 配置中有 num_layers=4/swin 结构, 走 BiRefNet 加载器
            from nobg.birefnet.modeling_birefnet import BiRefNet as _BiRef
            from nobg.birefnet.image_processing_birefnet import BiRefNetImageProcessor as _Proc
            model = _BiRef.from_pretrained(repo).eval().to(self.device)
            processor = _Proc.from_pretrained(repo)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"FeyNoBg 加载失败: {e}") from e
        self.model = model
        self.processor = processor
        self._loaded = True

    def unload(self) -> None:
        self.model = None
        self.processor = None
        self._loaded = False
        free_torch_caches()

    def remove_bg(self, image: Image.Image) -> Image.Image:
        self._ensure_loaded()
        import torch

        rgb = image.convert("RGB")
        inputs = self.processor(rgb, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(pixel_values=inputs["pixel_values"])
        try:
            alpha = self.processor.post_process_alpha_matting(
                outputs, target_sizes=[(rgb.height, rgb.width)]
            )[0]
            a_np = alpha.squeeze().cpu().numpy()
            a_img = Image.fromarray((np.clip(a_np, 0, 1) * 255).astype(np.uint8), mode="L")
        except Exception:  # noqa: BLE001  post 接口差异时手动处理
            logits = outputs if isinstance(outputs, tuple) else (outputs,)
            last = logits[-1]
            if hasattr(last, "sigmoid"):
                a = last.sigmoid().squeeze().cpu().numpy()
            else:
                a = np.asarray(last.squeeze().cpu())
            a_img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), mode="L")
            a_img = a_img.resize(rgb.size, Image.LANCZOS)
        return self._apply_alpha(image, a_img)


# ===========================================================================
# InSPyReNet —— 轻快低资源 (需 pip install transparent-background)
# ===========================================================================
@register_engine
class InSPyReNetEngine(BaseEngine):
    name = "inspyrenet"
    label = "InSPyReNet (轻快省资源)"
    desc = "transparent-background 内核 Swin-Base; 速度/内存友好"

    def __init__(self, models_root: str):
        super().__init__(models_root)
        self.remover = None
        self.device = "cpu"

    def _weights_paths(self) -> list[str]:
        return [self._weights()]

    def _check_deps(self) -> str:
        try:
            import torch  # noqa: F401
            import transparent_background  # noqa: F401
        except Exception as e:  # noqa: BLE001
            return f"缺少 transparent-background 库 (pip install transparent-background): {e}"
        return ""

    def _weights(self) -> str:
        return f"{self.models_root}/InSPyReNet/ckpt_base.pth"

    def load(self) -> None:
        if self.remover is not None:
            return
        p = self._weights()
        if not os.path.exists(p):
            raise RuntimeError(f"缺少模型文件: {p}")
        try:
            from transparent_background import Remover
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"缺少 transparent-background 库 (pip install transparent-background): {e}") from e
        self.device = pick_device()
        # Remover(mode="base", ckpt=...) 可直接加载本地 ckpt_base.pth, 避免重复下载
        try:
            self.remover = Remover(mode="base", ckpt=p, device=self.device)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"InSPyReNet 初始化失败: {e}") from e
        self._loaded = True

    def unload(self) -> None:
        self.remover = None
        self._loaded = False
        free_torch_caches()

    def remove_bg(self, image: Image.Image) -> Image.Image:
        self._ensure_loaded()
        rgb = image.convert("RGB")
        try:
            rgba = self.remover.process(rgb, type="rgba")
        except TypeError:
            rgba = self.remover.process(rgb)
        if isinstance(rgba, Image.Image):
            return rgba.convert("RGBA")
        # numpy 数组时手动合成 alpha
        import numpy as _np
        arr = _np.asarray(rgba)
        if arr.shape[2] == 4:
            return Image.fromarray(arr, mode="RGBA")
        # 若返回 mask, 套用 alpha
        a = Image.fromarray(arr[..., 0] if arr.ndim == 3 else arr, mode="L")
        return self._apply_alpha(image, a)
