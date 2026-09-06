#!/bin/bash
# ============================================================================
#  dst-mod-icon-matting - 模型权重下载器 (交互式 / 断点续传)
#
#  模型权重(每个 >100MB)受 GitHub 单文件 100MB 上限约束, 不随代码入库,
#  由本脚本按需下载。支持多选, 断网可续传 (Ctrl+C 后再跑会自动接着下)。
#
#  用法:
#    ./download_models.sh          # 交互选择要下载的模型
#    ./download_models.sh 1,3,5    # 或直接给编号 (1,3,5 / 3 5 / a)
# ============================================================================
cd "$(dirname "$0")"

# ---------- 模型元数据 ----------
# 格式: 编号|子目录|文件名|说明|官方URL|最小字节数(用于完成校验)
ITEMS=(
"1|models/RMBG-2.0|model.onnx|RMBG-2.0 均衡全能, 你常用的款, ~977MB, ONNX/CPU|https://modelscope.cn/models/briaai/RMBG-2.0/resolve/master/onnx/model.onnx|900000000"
"2|models/BEN2|BEN2_Base.onnx|BEN2 电商友好保留关联前景, ~213MB, ONNX/CPU|https://huggingface.co/PramaLLC/BEN2/resolve/main/BEN2_Base.onnx|200000000"
"3|models/BiRefNet|model.safetensors|BiRefNet 高精度发丝级边缘, ~425MB, MPS/GPU|https://huggingface.co/ZhengPeng7/BiRefNet/resolve/main/model.safetensors|400000000"
"4|models/FeyNoBg|model.safetensors|FeyNoBg 八项基准四项SOTA, ~900MB, MPS/GPU|https://huggingface.co/feyninc/FeyNobg/resolve/main/model.safetensors|850000000"
"5|models/InSPyReNet|ckpt_base.pth|InSPyReNet 轻快低资源, ~350MB, MPS/GPU|https://github.com/plemeri/transparent-background/releases/download/1.2.12/ckpt_base.pth|330000000"
)
N=${#ITEMS[@]}

# ---------- 小工具 ----------
file_size() {  # 字节数; 不存在返回 0
  stat -f%z "$1" 2>/dev/null || stat -c%s "$1" 2>/dev/null || echo 0
}
is_done() {  # $1=目录 $2=文件名 $3=最小字节
  local s; s=$(file_size "$1/$2")
  [ "$s" -ge "$3" ] 2>/dev/null
}

# 探测本机常见本地代理(用于下载加速), 没有就空
PROXY=""
for port in 7897 1087 7890 1080 8888; do
  if nc -z -G 1 127.0.0.1 "$port" 2>/dev/null; then
    PROXY="http://127.0.0.1:$port"
    break
  fi
done
[ -n "$PROXY" ] && echo "[信息] 检测到本地代理 $PROXY, 将优先走代理加速下载" || echo "[信息] 未检测到本地代理, 将直连下载 (国内可设置环境变量 HF_ENDPOINT=https://hf-mirror.com 提速)"

# ---------- 列表 ----------
list_items() {
  echo
  echo "可下载的抠图模型:"
  echo "  ─────────────────────────────────────────────────────────────"
  for i in $(seq 0 $((N-1))); do
    IFS='|' read -r no dir f desc url min <<< "${ITEMS[$i]}"
    local s
    if is_done "$dir" "$f" "$min"; then
      s="✅ 已下载"
    elif [ -f "$dir/$f" ]; then
      s="⏳ 不完整 ($(du -h "$dir/$f" 2>/dev/null | cut -f1))"
    else
      s="　未下载"
    fi
    printf "  %s)  %-22s %s\n" "$no" "$dir/$f" "$s"
    printf "      %s\n" "$desc"
  done
  echo "  ─────────────────────────────────────────────────────────────"
}

# ---------- 单个模型下载(循环续传) ----------
dl_one() { # $1=子目录 $2=文件名 $3=最小字节 $4=URL
  local dir="$1" f="$2" min="$3" url="$4" attempt=0
  mkdir -p "$dir"
  # 候选源: [官方, 官方走代理, hf-mirror 直连, hf-mirror 走代理]; 魔搭/github 无镜像时仅官方±代理
  local cand=()
  cand+=("$url|")
  [ -n "$PROXY" ] && cand+=("$url|$PROXY")
  case "$url" in
    *huggingface.co*)
      local mir="${url/https:\/\/huggingface.co/https:\/\/hf-mirror.com}"
      cand+=("$mir|")
      [ -n "$PROXY" ] && cand+=("$mir|$PROXY")
      ;;
  esac
  while [ $attempt -lt 600 ]; do
    attempt=$((attempt+1))
    for c in "${cand[@]}"; do
      local u="${c%%|*}" p="${c#*|}" extra=()
      if is_done "$dir" "$f" "$min"; then
        echo "[OK] $dir/$f 下载完整 ($(du -h "$dir/$f" | cut -f1))"
        return 0
      fi
      [ -n "$p" ] && extra=(-x "$p")
      echo "[↓] $dir/$f (轮次 $attempt, 当前 $(file_size "$dir/$f" | awk '{printf "%.0f", $1/1048576}') MB) ..."
      curl -s -L "${extra[@]}" -C - --connect-timeout 15 --max-time 500 --retry 2 --retry-delay 2 \
        -o "$dir/$f" "$u"
    done
    # 一轮候选全失败: 稍候再续
    [ $((attempt % 10)) -eq 0 ] && echo "    网络不稳? 已重试 $attempt 轮, 继续续传中..."
  done
  echo "[FAIL] $dir/$f 超过 600 轮仍未完成, 可再次运行本脚本续传"
  return 1
}

# ---------- 解析选择 ----------
parse_choice() {
  local raw="$1" ok=0
  case "$raw" in
    a|A|all) picked=(1 2 3 4 5); return 0 ;;
    q|Q|exit|quit) echo "已取消"; exit 0 ;;
  esac
  # 用空格/逗号/分号分隔的数字
  local n
  for n in $(echo "$raw" | tr ',; ' ' '); do
    [ -z "$n" ] && continue
    case "$n" in
      *[!0-9]*|'') echo "[错误] 无法识别: '$n'"; return 1 ;;
    esac
    if [ "$n" -ge 1 ] 2>/dev/null && [ "$n" -le "$N" ] 2>/dev/null; then
      # 去重
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

if [ $# -ge 1 ]; then
  CHOICE="$1"
else
  echo
  echo "请选择要下载的模型 (可多选, 用逗号/空格分隔, 如: 1,3,5)"
  echo "  a = 全部 5 个    q = 退出   再次运行本脚本可补下其它模型"
  read -r -p "你的选择 > " CHOICE
fi

picked=()
if ! parse_choice "$CHOICE"; then
  echo; echo "输入格式不对, 请参考上面示例重新运行。示例: ./download_models.sh 1,3,5"
  exit 1
fi

echo
echo "将下载以下模型:"
for x in "${picked[@]}"; do
  IFS='|' read -r no dir f desc url min <<< "${ITEMS[$((x-1))]}"
  if is_done "$dir" "$f" "$min"; then
    echo "  [$x] $f — 已存在且完整, 跳过"
  else
    echo "  [$x] $f — $desc"
  fi
done
echo

# 逐项启动(后台并行), 等待全部结束
pids=()
: > /tmp/dl_summary.$$
for x in "${picked[@]}"; do
  IFS='|' read -r no dir f desc url min <<< "${ITEMS[$((x-1))]}"
  ( dl_one "$dir" "$f" "$min" "$url"; echo "$? $x" >> /tmp/dl_summary.$$ ) &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done

echo
echo "=================== 下载结果 ==================="
okc=0
while read -r rc x; do
  [ -z "$x" ] && continue
  IFS='|' read -r no dir f desc url min <<< "${ITEMS[$((x-1))]}"
  if [ "$rc" = "0" ] && is_done "$dir" "$f" "$min"; then
    echo "  ✅ [$x] $dir/$f"
    okc=$((okc+1))
  else
    echo "  ❌ [$x] $dir/$f 未完成 (断网可重跑本脚本续传)"
  fi
done < /tmp/dl_summary.$$
rm -f /tmp/dl_summary.$$
echo "================================================"

if [ "$okc" -gt 0 ]; then
  echo
  echo "🎉 下载完成 $okc 个模型。现在可以启动工具了:"
  echo "   ./run.sh      # 启动后浏览器打开 http://127.0.0.1:7860"
  echo "   (如需补下其它模型, 再次运行 ./download_models.sh 即可)"
fi
[ "$okc" -lt "${#picked[@]}" ] && exit 1
exit 0
