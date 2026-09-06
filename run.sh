#!/bin/bash
# 本地 AI 抠图工具 - 一键启动
# 说明: 工具运行时是纯本地的, 不需要网络也不需要代理。
#       网络仅用于两件事(均只发生一次):
#         · 首次创建虚拟环境时 pip 下载依赖
#         · 首次启动发现没有模型权重时, 引导运行 download_models.sh 按需下载
cd "$(dirname "$0")"

# 判断 .venv 是否"完整可用": 目录存在 且 有 python 且 有 pip
# (缺 pip 说明上次创建被中断/半成品, 需走 setup.sh 重建; 否则会拿坏环境直接启动报错)
if [ ! -d ".venv" ] || [ ! -x ".venv/bin/python" ] || [ ! -x ".venv/bin/pip" ]; then
  echo "[首次运行] 尚未配置运行环境 (虚拟环境/依赖 缺失或不完整)。"
  echo "          现在进入引导: 选择你要用的模型 → 只安装它需要的依赖 → 下载对应权重。"
  echo "          之后每次启动不再需要网络。"
  echo
  ./setup.sh || exit 1
  echo
  echo "环境配置完成, 继续启动..."
fi

# 模型权重检查: 5 个权重都很大(>100MB, GitHub 无法入库), 需按需下载。
# 若一个都没有, 自动进入交互选择; 若只有一部分, 提示可随时补下。
MISSING=0
TOTAL=5
for w in \
  models/RMBG-2.0/model.onnx \
  models/BEN2/BEN2_Base.onnx \
  models/BiRefNet/model.safetensors \
  models/FeyNoBg/model.safetensors \
  models/InSPyReNet/ckpt_base.pth; do
  [ -f "$w" ] || MISSING=$((MISSING+1))
done

if [ "$MISSING" = "$TOTAL" ]; then
  echo "[首次使用] 尚未下载任何模型权重。"
  echo "  每个模型 200MB~1GB, 建议先按需下载 1~2 个就能用 (可随时补下):"
  echo "  常用 RMBG-2.0(均衡) 或 InSPyReNet(轻快), 追求细节选 BiRefNet/FeyNoBg"
  ./download_models.sh || exit 1
elif [ "$MISSING" -gt 0 ]; then
  echo "[信息] 有 $MISSING 个模型未下载 (缺 $MISSING/5)。想补充可运行: ./download_models.sh"
fi

echo
echo "启动 Web 界面: http://127.0.0.1:7860"
echo "(工具为纯本地离线运行: 不上传图片、不调用云端, 断网可用)"
exec ./.venv/bin/python app.py
