# -*- coding: utf-8 -*-
"""
本地 AI 抠图工具 - 引擎包
统一接口: 每个引擎实现 BaseEngine, 提供 name / info / load / remove_bg

本工具为纯本地离线运行: 抠图不调用任何云端接口、不上传图片。
在导入任何 transformers / huggingface_hub 之前强制设为离线模式,
确保模型加载只读本地 models/ 目录, 绝不联网(断网可用)。
"""
import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")          # huggingface_hub 完全离线
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")     # transformers 不访问网络
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")  # 关闭遥测上报

from .base import BaseEngine, register_engine, get_engines, list_engine_names

__all__ = ["BaseEngine", "register_engine", "get_engines", "list_engine_names"]
