# -*- coding: utf-8 -*-
"""引擎基类与注册表。每个抠图模型实现为一个 BaseEngine 子类。"""
from __future__ import annotations

import abc
import os
from typing import Optional

from PIL import Image


class BaseEngine(abc.ABC):
    """抠图引擎统一接口。

    - ``name``: 唯一标识（英文小写），用于 UI 下拉框 value
    - ``label``: 展示名称（中文），用于 UI 下拉框显示
    - ``desc``:  简短说明（特点/适用场景）
    - ``load()``: 加载模型到内存/设备，幂等，失败抛异常
    - ``remove_bg(image) -> RGBA Image``: 输入 RGB/RGBA PIL 图，返回带 alpha 的图
    """

    name: str = ""
    label: str = ""
    desc: str = ""
    needs_download: Optional[list] = None  # 缺什么文件会给出提示

    def __init__(self, models_root: str):
        self.models_root = models_root
        self._loaded = False
        self._device = None
        self._load_error: Optional[str] = None

    @abc.abstractmethod
    def load(self) -> None:
        """加载权重。必须幂等（可多次调用）。失败抛 RuntimeError 说明原因。"""

    @abc.abstractmethod
    def remove_bg(self, image: Image.Image) -> Image.Image:
        """返回透明背景结果 (RGBA)。"""

    # ---- 通用辅助 ----
    def _ensure_loaded(self):
        if not self._loaded:
            self.load()
            self._loaded = True

    def probe_ready(self) -> tuple[bool, str]:
        """轻量探测: 不加载权重, 只检查关键文件与依赖库。

        返回 (是否可用, 原因)。缺文件/缺库会返回 False + 指引。
        """
        missing = [p for p in self._weights_paths() if not os.path.exists(p)]
        if missing:
            return False, "缺少权重文件: " + ", ".join(missing)
        dep_err = self._check_deps()
        if dep_err:
            return False, dep_err
        return True, ""

    def _check_deps(self) -> str:
        """返回缺失依赖提示; 无缺失返回空串。子类可覆写。"""
        return ""

    def check_files(self) -> bool:
        """默认检查权重文件是否存在(由 _weights_paths() 提供)。子类按需覆写。"""
        for p in self._weights_paths():
            if not os.path.exists(p):
                return False
        return True

    def _weights_paths(self) -> list[str]:
        return []

    def is_available(self) -> bool:
        """是否能正常加载（不抛异常）。用于启动时探测并回填下拉框。"""
        try:
            self._ensure_loaded()
            return True
        except Exception as e:  # noqa: BLE001
            self._load_error = str(e)
            return False

    def _to_rgba(self, image: Image.Image) -> Image.Image:
        image = image.convert("RGBA")
        return image

    def _apply_alpha(self, image: Image.Image, alpha: Image.Image) -> Image.Image:
        """用灰度 alpha 图合并到原图，输出 RGBA。alpha 会被 resize 到原图尺寸。"""
        rgba = self._to_rgba(image)
        if alpha.size != rgba.size:
            alpha = alpha.resize(rgba.size, Image.LANCZOS)
        a = alpha.convert("L")
        rgba.putalpha(a)
        return rgba

    @property
    def loaded(self) -> bool:
        """模型权重是否已加载进内存。"""
        return self._loaded

    def unload(self) -> None:
        """释放已加载的模型权重, 释放后可再次 load()。

        基类默认只清标志位; 子类必须覆写以置空实际模型引用
        (如 self.model/session/remover = None), 否则内存不会被回收。
        """
        self._loaded = False

    def __repr__(self):
        return f"<Engine {self.name} loaded={self._loaded}>"


# ---------------------------------------------------------------------------
# 注册表
# ---------------------------------------------------------------------------
_ENGINES: dict[str, type[BaseEngine]] = {}


def register_engine(cls: type[BaseEngine]) -> type[BaseEngine]:
    if not cls.name:
        raise ValueError(f"engine class {cls.__name__} must define name")
    _ENGINES[cls.name] = cls
    return cls


def list_engine_names() -> list[str]:
    return list(_ENGINES.keys())


def get_engines(models_root: str) -> list[BaseEngine]:
    return [cls(models_root) for cls in _ENGINES.values()]


# ---------------------------------------------------------------------------
# 内存辅助
# ---------------------------------------------------------------------------
def free_torch_caches() -> None:
    """回收 Python 引用计数垃圾; 若 torch 已被导入, 顺带清空其 MPS/CUDA 缓存。

    注意: torch 未导入时不会主动 import(避免纯 ONNX 场景被误拉入 torch 内存)。
    """
    import gc
    import sys

    gc.collect()
    if "torch" not in sys.modules:
        return
    try:
        import torch

        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


def current_rss_mb() -> int:
    """当前进程 RSS(物理内存), MB。失败返回 0。"""
    try:
        import psutil

        return int(psutil.Process().memory_info().rss / 1048576)
    except Exception:  # noqa: BLE001
        return 0
