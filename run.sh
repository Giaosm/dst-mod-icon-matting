#!/bin/bash
# 本地 AI 抠图工具 - 一键启动
# 说明: 工具运行时是纯本地的, 不需要网络也不需要代理。
#       网络仅用于两件事(均只发生一次):
#         · 首次创建虚拟环境时 pip 下载依赖
#         · 首次启动发现没有模型权重时, 引导运行 download_models.sh 按需下载
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "[首次运行] 创建虚拟环境并安装依赖 (需联网, 约几分钟)..."
  python3 -m venv .venv

  # 仅此步骤可能需要网络: 若本机有常见本地代理则自动加速下载, 否则直连
  PIP_PROXY=""
  for port in 7897 1087 1080 8888 7890; do
    if nc -z -G 1 127.0.0.1 "$port" 2>/dev/null; then
      PIP_PROXY="--proxy http://127.0.0.1:$port"
      echo "[信息] 检测到本地代理 127.0.0.1:$port, 用于加速依赖下载"
      break
    fi
  done

  ./.venv/bin/pip install -U pip $PIP_PROXY
  ./.venv/bin/pip install -r requirements.txt $PIP_PROXY || {
    echo "[错误] 依赖安装失败。若网络受限可尝试:"
    echo "  export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"
    echo "  或去掉下方 run.sh 中代理相关逻辑后重试。"
    exit 1
  }
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
