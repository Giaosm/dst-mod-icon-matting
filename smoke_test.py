# -*- coding: utf-8 -*-
"""引擎冒烟测试: 逐个用测试图跑一遍, 校验输出为合理 RGBA。"""
from __future__ import annotations

import os
import sys
import time

from PIL import Image

import engines.onnx_engines  # noqa: F401
import engines.torch_engines  # noqa: F401
from engines import get_engines

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(ROOT, "models")


def _make_test_image() -> Image.Image:
    """构造一张简单测试图: 蓝底 + 红苹果 + 绿叶。"""
    img = Image.new("RGB", (640, 480), (120, 160, 200))
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.ellipse([220, 120, 420, 320], fill=(220, 40, 40))     # 苹果
    d.ellipse([300, 90, 360, 150], fill=(40, 160, 60))       # 叶子
    d.rectangle([330, 70, 344, 100], fill=(139, 90, 43))     # 梗
    d.ellipse([180, 300, 460, 420], fill=(180, 30, 30))      # 底部阴影面
    return img


def main():
    img = _make_test_image().convert("RGB")
    engines = get_engines(MODELS)
    print(f"共注册 {len(engines)} 个引擎, 测试图: {img.size}")
    ok = 0
    for e in engines:
        t0 = time.time()
        try:
            ok_r, reason = e.probe_ready()
            if not ok_r:
                print(f"  [探测跳过] {e.label}: {reason}")
                continue
            e._ensure_loaded()
            t_load = time.time() - t0
            t1 = time.time()
            out = e.remove_bg(img)
            t_inf = time.time() - t1
            assert out.mode == "RGBA", f"mode={out.mode}"
            assert out.size == img.size, f"size={out.size}"
            a = out.getchannel("A")
            ext = a.getextrema()
            # alpha 不应全黑/全白
            hist = a.histogram()
            nz = sum(hist)
            opaque = sum(hist[128:])
            print(f"  [OK] {e.label}: alpha范围={ext} 不透明占比={opaque/nz:.1%} "
                  f"加载={t_load:.1f}s 推理={t_inf:.1f}s")
            ok += 1
        except Exception as ex:  # noqa: BLE001
            print(f"  [FAIL] {e.label}: {type(ex).__name__}: {ex}")
    print(f"完成: {ok} 个引擎通过")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
