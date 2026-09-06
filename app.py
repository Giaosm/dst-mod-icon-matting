# -*- coding: utf-8 -*-
"""
本地 AI 抠图工具 —— Gradio Web 界面
启动:  python app.py   (或 ./run.sh)
浏览器打开 http://127.0.0.1:7860

内存策略:
- single: 同一时刻只驻留一个模型, 切换模型自动释放旧模型 (默认, 省内存)
- cache : 模型加载后常驻, 切换秒回, 但多模型会占用大量内存
"""
from __future__ import annotations

import os
import threading
import time

import gradio as gr

# 注册所有引擎 (import 即有注册副作用)
import engines.onnx_engines  # noqa: F401
import engines.torch_engines  # noqa: F401
from engines import get_engines
from engines.base import current_rss_mb, free_torch_caches
from engines.common import ensure_dir

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS_ROOT = os.path.join(PROJECT_ROOT, "models")
OUTPUT_DIR = ensure_dir(os.path.join(PROJECT_ROOT, "output"))

# 串行化「加载+推理」临界区, 避免并发请求同时加载多个模型把内存打爆
_RUN_LOCK = threading.Lock()

# 各模型运行时内存占用(GB, 实测近似值; RMBG/BEN2 为 CPU-ONNX 瞬时需求较高)
_MEM_HINT = {
    "rmbg-2.0": "⚠️ 高内存: 瞬时 ≈8 GB, 慢",
    "ben2": "⚠️ 高内存: 瞬时 ≈3.5 GB",
    "birefnet": "≈1.5 GB",
    "feynobg": "≈1 GB (最快)",
    "inspyrenet": "≈1 GB (推荐先用这个)",
}
# 默认选中的模型: RMBG-2.0 (用户常用)
_DEFAULT_MODEL = "rmbg-2.0"
# 内存策略默认值: 抠完即释放 (最省内存)
_DEFAULT_MEM_MODE = "auto"


def build_status():
    """启动探测: 返回 (可用引擎实例列表, HTML 状态面板)。"""
    all_engines = get_engines(MODELS_ROOT)
    ready = []
    rows = []
    for e in all_engines:
        ok, reason = e.probe_ready()
        if ok:
            ready.append(e)
            rows.append(f'<div style="color:#16a34a">✅ <b>{e.label}</b> — {_MEM_HINT.get(e.name, "")}</div>')
        else:
            rows.append(f'<div style="color:#b45309">⚠️ <b>{e.label}</b> — {reason}</div>')
    return ready, '<div style="font-size:14px;line-height:1.9">' + "".join(rows) + "</div>"


def _evict_all(ready_engines) -> None:
    """释放所有已加载模型的内存。"""
    for e in ready_engines:
        if e.loaded:
            try:
                e.unload()
            except Exception:  # noqa: BLE001
                pass
    free_torch_caches()


def build_ui():
    ready_engines, status_html = build_status()
    choices = [e.name for e in ready_engines]
    default_model = _DEFAULT_MODEL if _DEFAULT_MODEL in choices else (choices[0] if choices else None)

    def run_remove_bg(image, model_name, mem_mode, progress=gr.Progress()):
        if image is None:
            raise gr.Error("请先上传图片")
        with _RUN_LOCK:
            # 内存模式: auto/single 下, 运行前先释放其它已加载模型(只留当前 1 个)
            freed = False
            if mem_mode in ("auto", "single"):
                for e in ready_engines:
                    if e.loaded and e.name != model_name:
                        try:
                            e.unload()
                            freed = True
                        except Exception:  # noqa: BLE001
                            pass
                if freed:
                    free_torch_caches()
            eng = next((e for e in ready_engines if e.name == model_name), None)
            if eng is None:
                raise gr.Error("该模型当前不可用, 请查看上方状态说明")

            t0 = time.time()
            if not eng.loaded:
                progress(0.1, desc=f"加载模型 {eng.label} (首次较慢)…")
            try:
                eng._ensure_loaded()
            except Exception as ex:  # noqa: BLE001
                raise gr.Error(f"模型加载失败: {ex}")
            load_s = time.time() - t0

            progress(0.5, desc=f"抠图中 ({eng.label})…")
            try:
                out = eng.remove_bg(image)
            except Exception as ex:  # noqa: BLE001
                raise gr.Error(f"推理失败: {ex}")
            elapsed = time.time() - t0
            # 落到磁盘, 供下载
            safe = f"output_{model_name}_{int(time.time())}.png"
            out_path = os.path.join(OUTPUT_DIR, safe)
            out.save(out_path)

            # 内存策略: auto = 抠完立即释放当前模型 (最省内存)
            freed_now = False
            if mem_mode == "auto":
                try:
                    eng.unload()
                    freed_now = True
                except Exception:  # noqa: BLE001
                    pass
            free_torch_caches()
            progress(1.0, desc="完成 (已释放模型内存)" if freed_now else "完成")
            mem_mb = current_rss_mb()
            # 返回: 透明图 / 运行信息 / 下载路径
            info = (
                f"模型: {eng.label}  |  耗时 {elapsed:.1f}s"
                + (f" (加载 {load_s:.1f}s)" if load_s > 0.5 else "")
                + f"  |  进程内存 ≈{mem_mb} MB"
                + ("  |  ✅ 抠完已自动释放内存" if freed_now else "")
            )
            return out_path, info

    def release_all():
        """手动释放全部已加载模型。"""
        with _RUN_LOCK:
            _evict_all(ready_engines)
        return f"已释放全部模型内存, 当前进程 ≈{current_rss_mb()} MB"

    with gr.Blocks(title="AI 抠图工具") as demo:
        gr.Markdown(
            "# 🖼️ 本地 AI 抠图工具\n"
            "**纯本地推理, 图片不上传**。选模型 → 传图 → 去背景。上方状态已标注每个模型的内存占用；"
            "默认「抠完即释放」策略——每次抠完**自动释放模型内存**，无需手动操作。"
        )
        with gr.Row():
            with gr.Column(scale=3):
                status_box = gr.HTML(status_html)
                model_drop = gr.Dropdown(
                    choices=choices,
                    value=default_model,
                    label="抠图模型",
                    info="默认 RMBG-2.0(均衡全能); 要更好细节选 BiRefNet/FeyNoBg; RMBG/BEN2 为 CPU 推理较慢, 已默认自动释放内存",
                )
                mem_mode = gr.Radio(
                    choices=[
                        ("♻️ 抠完即释放 (默认, 最省内存)", "auto"),
                        ("💧 单模型驻留·切换才释放", "single"),
                        ("⏩ 全缓存·连续抠最快", "cache"),
                    ],
                    value=_DEFAULT_MEM_MODE,
                    label="内存策略",
                    info="auto: 每次抠完立即释放模型, 内存始终低位(代价: 每次重新加载); single: 保留当前模型, 切换才释放; cache: 用过即常驻, 连续用最快但吃内存",
                )
                inp = gr.Image(type="pil", label="上传图片", sources=["upload", "clipboard"])
                btn = gr.Button("✨ 开始抠图", variant="primary")
                release_btn = gr.Button("🧹 释放已加载模型 (释放内存)")
            with gr.Column(scale=3):
                out_img = gr.Image(type="filepath", label="抠图结果 (透明背景 PNG)", interactive=False)
                info_box = gr.Textbox(label="运行信息 (耗时 / 内存)", interactive=False)
                download = gr.File(label="下载 PNG")

        btn.click(run_remove_bg, inputs=[inp, model_drop, mem_mode], outputs=[out_img, info_box]).then(
            lambda p: p, inputs=[out_img], outputs=[download]
        )
        release_btn.click(release_all, outputs=[info_box])
        gr.Examples(
            examples=[],
            inputs=inp,
            label="提示: 支持拖入/粘贴图片; 人物、商品、宠物等主体效果最佳",
        )
    return demo, len(ready_engines)


def main():
    demo, n = build_ui()
    if n == 0:
        print("[警告] 没有任何可用模型! 请检查 models/ 目录权重是否齐全、依赖是否安装。")
    print(f"[信息] 可用模型数: {n}  | 默认模型: RMBG-2.0 | 内存策略: 抠完即释放(auto)")
    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        show_error=True,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
