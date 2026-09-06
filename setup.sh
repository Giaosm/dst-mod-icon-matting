#!/bin/bash
# ============================================================================
#  dst-mod-icon-matting - 按需安装器 (依赖 + 权重)
#
#  原则: 先选模型 → 只安装该模型需要的依赖 → 只下载该模型的权重。
#  - 选 RMBG-2.0 / BEN2 → 只需 onnxruntime (轻, 几十MB), 不用装 torch(~2GB)
#  - 选 BiRefNet / FeyNoBg / InSPyReNet → 才需要 torch 系列
#
#  用法:
#    ./setup.sh            # 交互选择要安装的模型
#    ./setup.sh 1,3,5      # 或直接给编号 (可重复运行来补装其它模型)
# ============================================================================
cd "$(dirname "$0")"

# ---------- 模型元数据: 编号|显示名|依赖组(空格分隔) ----------
# 依赖组对应: core(必装) onnx torch birefnet feynobg inspyrenet
ITEMS=(
"1|RMBG-2.0|onnx"
"2|BEN2|onnx"
"3|BiRefNet|torch birefnet"
"4|FeyNoBg|torch feynobg"
"5|InSPyReNet|torch inspyrenet"
)
N=${#ITEMS[@]}

# ---------- 列表(含是否可用的简评) ----------
list_items() {
  echo
  echo "可用模型与所需依赖:"
  echo "  ─────────────────────────────────────────────────────────────────"
  echo "  1) RMBG-2.0     均衡全能(你常用的款)     依赖: ONNX 系, 轻 (~几十 MB)"
  echo "  2) BEN2         电商友好保留关联前景       依赖: ONNX 系, 轻"
  echo "  3) BiRefNet     发丝级高精度, 细节最好     依赖: PyTorch 系 (~2 GB)"
  echo "  4) FeyNoBg      八项基准四项 SOTA, 最快   依赖: PyTorch 系 (~2 GB)"
  echo "  5) InSPyReNet   轻快低资源                依赖: PyTorch 系 (~2 GB)"
  echo "  ─────────────────────────────────────────────────────────────────"
  echo "  提示: 首次先选 1 个就够用; 以后想加模型再运行 ./setup.sh 补装即可"
  echo "        (已装好的依赖/权重会自动跳过, 不会重复下载)"
}

# ---------- 解析选择 ----------
parse_choice() {
  local raw="$1"
  case "$raw" in
    a|A|all) picked=(1 2 3 4 5); return 0 ;;
    q|Q|exit|quit) echo "已取消"; exit 0 ;;
  esac
  local n
  for n in $(echo "$raw" | tr ',; ' ' '); do
    [ -z "$n" ] && continue
    case "$n" in
      *[!0-9]*|'') echo "[错误] 无法识别: '$n'"; return 1 ;;
    esac
    if [ "$n" -ge 1 ] 2>/dev/null && [ "$n" -le "$N" ] 2>/dev/null; then
      local dup=0 x
      for x in "${picked[@]:-}"; do [ "$x" = "$n" ] && dup=1; done
      [ "$dup" = "0" ] && picked+=("$n")
    else
      echo "[错误] 编号越界: '$n' (应在 1-$N 之间)"; return 1
    fi
  done
  [ ${#picked[@]} -gt 0 ] && return 0 || return 1
}

# ---------- 主流程 ----------
list_items
echo
echo "请选择要安装的模型 (可多选, 用逗号/空格分隔, 如: 1,3,5)"
echo "  a = 全部 5 个    q = 退出"
if [ $# -ge 1 ]; then
  CHOICE="$1"
  echo "已按参数选择: $CHOICE"
else
  read -r -p "你的选择 > " CHOICE
fi

picked=()
if ! parse_choice "$CHOICE"; then
  echo; echo "输入格式不对, 请参考示例重新运行。示例: ./setup.sh 1,3,5"
  exit 1
fi

# ---- 推导需要哪些依赖组 ----
groups="core"
for x in "${picked[@]}"; do
  IFS='|' read -r no nm g <<< "${ITEMS[$((x-1))]}"
  for grp in $g; do
    case " $groups " in
      *" $grp "*) : ;;            # 已有
      *) groups="$groups $grp" ;;
    esac
  done
done

echo
echo "将安装以下模型的依赖:"
names=""
for x in "${picked[@]}"; do
  IFS='|' read -r no nm g <<< "${ITEMS[$((x-1))]}"
  names="$names $nm"
done
echo "  模型: $names"

# 依赖 → pip 参数
PIP_ARGS="-r requirements-core.txt"
case " $groups " in
  *" onnx "*)      PIP_ARGS="$PIP_ARGS -r requirements-onnx.txt";     echo "  [依赖] onnxruntime (RMBG-2.0 / BEN2)";;
esac
case " $groups " in
  *" torch "*)     PIP_ARGS="$PIP_ARGS -r requirements-torch.txt";    echo "  [依赖] torch + torchvision (PyTorch 系, ~2GB, 需下载较久)";;
esac
case " $groups " in
  *" birefnet "*)  PIP_ARGS="$PIP_ARGS -r requirements-birefnet.txt"; echo "  [依赖] transformers/timm/einops/kornia (BiRefNet)";;
esac
case " $groups " in
  *" feynobg "*)   PIP_ARGS="$PIP_ARGS nobg>=0.2.5";                  echo "  [依赖] nobg (FeyNoBg)";;
esac
case " $groups " in
  *" inspyrenet "*) PIP_ARGS="$PIP_ARGS transparent-background";      echo "  [依赖] transparent-background (InSPyReNet)";;
esac

# ---- 探测代理(仅安装需要; 有则加速) ----
PIP_PROXY=""
for port in 7897 1087 1080 8888 7890; do
  if nc -z -G 1 127.0.0.1 "$port" 2>/dev/null; then
    PIP_PROXY="--proxy http://127.0.0.1:$port"
    echo "  [信息] 检测到本地代理 127.0.0.1:$port, 用于加速依赖下载"
    break
  fi
done

# ---- 干跑预览 (SETUP_DRY_RUN=1 时不实际安装/下载) ----
if [ -n "$SETUP_DRY_RUN" ]; then
  echo
  echo "[DRY-RUN] 预览模式(未执行任何安装/下载):"
  echo "  pip install $PIP_ARGS"
  echo "  ./download_models.sh $CHOICE"
  exit 0
fi

# ---- 解释器准备: 有现成的就用, 没有再自动装一个 Python 3.12 (不拦人) ----
#   1) 项目已有 .venv            → 直接复用 (不管当初是用什么建的)
#   2) 系统里找 Python 3.10+     → 用它来创建 .venv (候选含 Homebrew 目录, 不在 PATH 也能命中)
#   3) 都没有                    → 自动安装 Python 3.12:
#        macOS + 有 Homebrew     → brew install python@3.12   (macOS 惯例)
#        其它 (Linux / 无 brew)  → 用 uv 下载到用户目录, 免 sudo 不动系统
PY=""

# uv 兜底: 下载 Python 3.12 到用户目录 (~/.local/share/uv), 不影响系统
install_python_via_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "  [1/2] 下载 uv (~15MB) ..."
    _uv_tmp="$(mktemp -d 2>/dev/null || echo /tmp)"
    if ! curl -fsSL https://astral.sh/uv/install.sh -o "$_uv_tmp/uv-install.sh" 2>/dev/null; then
      echo
      echo "[错误] 自动下载失败 (无法联网下载 uv)。装好 uv 后重跑 ./setup.sh:"
      echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
      rm -rf "$_uv_tmp"; exit 1
    fi
    if ! sh "$_uv_tmp/uv-install.sh" >/dev/null 2>&1; then
      echo
      echo "[错误] uv 安装失败。请手动执行:  curl -LsSf https://astral.sh/uv/install.sh | sh"
      rm -rf "$_uv_tmp"; exit 1
    fi
    rm -rf "$_uv_tmp"
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv >/dev/null 2>&1 || {
      echo "[错误] uv 装好后仍不可用。请手动安装后重跑 ./setup.sh"; exit 1
    }
  fi
  echo "  [2/2] 下载 Python 3.12 ..."
  uv python install 3.12 || {
    echo "[错误] Python 下载失败。请检查网络后重跑 ./setup.sh (已下载部分会自动跳过)。"
    exit 1
  }
  PY="$(uv python find 3.12)" || exit 1
}

if [ -x ".venv/bin/python" ]; then
  PY="./.venv/bin/python"
  echo "[信息] 复用已有虚拟环境 .venv: $("$PY" --version 2>&1)"
else
  # 2) 候选: 常用命令名 + Homebrew 两个安装目录 (Apple Silicon 在 /opt/homebrew, Intel 在 /usr/local)
  _cands="python3.13 python3.12 python3.11 python3.10 python3"
  for _bp in /opt/homebrew/bin /usr/local/bin; do
    for _c in python3.13 python3.12 python3.11 python3.10; do
      [ -x "$_bp/$_c" ] && _cands="$_cands $_bp/$_c"
    done
  done
  for _c in $_cands; do
    if command -v "$_c" >/dev/null 2>&1 && \
       "$_c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
      PY="$_c"; break
    fi
  done
  if [ -n "$PY" ]; then
    echo "[信息] 使用 Python: $("$PY" --version 2>&1)  ($(command -v "$PY"))"
  else
    # 3) 系统里确实没有 → 自动安装
    case "$(uname -s)" in
      Darwin)
        if command -v brew >/dev/null 2>&1; then
          echo
          echo "[提示] 本机没有 Python 3.10+。将用 Homebrew 安装 python@3.12 (macOS 惯例)..."
          echo "  执行: brew install python@3.12    (需几分钟, 请稍候)"
          if ! brew install python@3.12; then
            echo
            echo "[错误] brew 安装失败。可手动执行上面的命令, 装好后重跑 ./setup.sh"
            exit 1
          fi
          if [ -x /opt/homebrew/bin/python3.12 ]; then PY="/opt/homebrew/bin/python3.12"
          elif [ -x /usr/local/bin/python3.12 ]; then PY="/usr/local/bin/python3.12"
          else PY="$(command -v python3.12 2>/dev/null)"; fi
          if [ -z "$PY" ] || [ ! -x "$PY" ]; then
            echo "[错误] 找不到 Homebrew 安装的 python3.12, 请手动确认后重跑 ./setup.sh"; exit 1
          fi
        else
          echo
          echo "[提示] 本机没有 Python 3.10+ 也没有 Homebrew。"
          echo "       将自动用 uv 下载一个 Python 3.12 到用户目录 (不影响系统)。"
          echo "       (想改用 Homebrew: 先装它再重跑 ——"
          echo "        /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\")"
          echo
          install_python_via_uv
        fi
        ;;
      *)
        echo
        echo "[提示] 本机没有 Python 3.10+。将自动用 uv 下载一个 Python 3.12"
        echo "       到用户目录 (免 sudo, 不影响系统)。"
        echo
        install_python_via_uv
        ;;
    esac
    echo "[信息] Python 3.12 已就绪: $("$PY" --version 2>&1)"
  fi
fi

# ---- 创建 venv + 安装 ----
if [ ! -d ".venv" ]; then
  echo
  echo "创建虚拟环境 .venv ..."
  if ! "$PY" -m venv .venv; then
    echo "[错误] 创建 venv 失败, 请确认 $PY 完整可用 (运行 $PY --version 检查)"
    exit 1
  fi
fi

echo
echo "安装依赖 (仅所选模型的, 已装的会秒跳过)..."
./.venv/bin/pip install -U pip $PIP_PROXY
./.venv/bin/pip install $PIP_ARGS $PIP_PROXY || {
  echo
  echo "[错误] 依赖安装失败。若网络受限可尝试:"
  echo "  export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"
  echo "  然后重新运行 ./setup.sh (已下载的部分会断点续传/跳过)"
  exit 1
}

# ---- 下载所选模型权重 (已存在且完整的会自动跳过) ----
echo
echo "检查并下载所选模型的权重 (已下载过的会自动跳过)..."
./download_models.sh "$CHOICE" || {
  echo
  echo "[提示] 权重下载未全部完成 (可能是网络中断)。重跑 ./setup.sh $CHOICE 可断点续传。"
}

echo
echo "✅ 环境配置完成! 启动工具:"
echo "   ./run.sh      # 浏览器打开 http://127.0.0.1:7860"
echo "   (想补装其它模型: ./setup.sh  或  ./download_models.sh)"
