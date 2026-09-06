# 🖼️ 本地 AI 抠图工具

纯本地运行的 AI 背景移除工具：图片**不上传任何服务器**，5 个开源抠图模型可切换，
带中文 Web 界面，支持拖拽 / 粘贴图片，一键输出透明背景 PNG。

> 模型权重来自 `models/` 目录（来源与协议见 `models/来源与说明.txt`）。
> 权重文件每个 >100MB，超出 GitHub 单文件上限，**不随仓库分发**，由安装引导按需下载。

---

## 一、部署前需要准备什么

| 项目 | 要求 |
| --- | --- |
| 操作系统 | macOS 或 Linux（一键脚本基于 bash；Windows 见下方 FAQ） |
| Python | **3.10 或更高**（推荐 3.11 / 3.12，下面教你确认和安装） |
| 内存 | 建议 8 GB 以上（个别模型瞬时峰值约 8 GB） |
| 磁盘 | 程序约 0.5 GB；模型权重每个 0.2 ~ 1 GB，按需下载 |
| 网络 | **仅首次安装时需要**（下依赖 + 下权重）；装好之后可完全断网使用 |

> 首次部署只需选 1 个模型即可开始（如 RMBG-2.0，权重约 1 GB），
> 总耗时取决于网速，一般几分钟到十几分钟。

---

## 二、从零部署（新手跟着做就行）

下面每一步都给出要执行的命令，复制粘贴到终端里回车即可。

### 第 1 步 · 打开「终端」

- **macOS**：按 `⌘ + 空格`，输入 `终端`（或 Terminal），回车；
- **Linux**：按 `Ctrl + Alt + T`。

### 第 2 步 · 确认 Python 版本

在终端粘贴执行：

```bash
python3 --version
```

- 显示 **3.10 或更高**（如 `Python 3.12.7`）→ 直接进入第 3 步；
- 提示 `command not found`，或版本 **低于 3.10** → 先安装：

  - **macOS**：打开 <https://www.python.org/downloads/>，下载 **3.12.x** 安装包，
    双击后一路点「继续」装完即可。（若装了 Homebrew，也可 `brew install python@3.12`）
  - **Linux Debian / Ubuntu**：`sudo apt update && sudo apt install python3 python3-venv`
  - **Linux Fedora**：`sudo dnf install python3`

  装完重新执行一次 `python3 --version`，确认能显示 3.10+ 再继续。

### 第 3 步 · 获取项目代码（二选一）

**方式 A：用 git 克隆（推荐，以后更新方便）**

```bash
git clone https://github.com/Giaosm/dst-mod-icon-matting.git
cd dst-mod-icon-matting
```

**方式 B：下载 ZIP 压缩包**

打开仓库页面 → 点绿色的 **Code** 按钮 → **Download ZIP** → 解压。
然后在终端进入解压出来的目录（路径换成你实际的，可用 `ls` 确认里面有 `run.sh`）：

```bash
cd ~/Downloads/dst-mod-icon-matting
```

### 第 4 步 ·（只有方式 B 需要）给脚本加执行权限

ZIP 解压会丢失脚本的「可执行」权限，先执行一次（方式 A 可跳过）：

```bash
chmod +x run.sh setup.sh download_models.sh
```

### 第 5 步 · 一键启动（首次运行 = 自动进入安装引导）

```bash
./run.sh
```

第一次运行时会自动进入安装引导：列出 5 个模型让你选，
然后**只安装所选模型需要的依赖**，并下载对应权重。

### 第 6 步 · 选择要用的模型

看到 `你的选择 >` 时，输入模型编号后回车。

**第一次建议只选 `1`（RMBG-2.0）**——均衡够用、依赖最轻（不用下载约 2 GB 的 PyTorch）：

```
你的选择 > 1
```

各编号对应哪个模型、适合什么场景，见下文「五、支持的模型」。
以后想加装其它模型，随时可补（见「三、以后怎么用」）。

### 第 7 步 · 等待自动完成「装依赖 + 下权重」

引导会自动完成两步，**全程无需操作**：

1. **安装依赖**：先创建虚拟环境 `.venv`，只装所选模型需要的依赖（已装过的秒跳过）；
2. **下载模型权重**（约 0.2 ~ 1 GB）：有进度显示。中途断网或取消没关系，
   **重新运行会自动断点续传**，不会从头再来。

> 若终端出现 `检测到本地代理`，只是装依赖时走了本机代理加速，属正常提示，不影响之后使用。

### 第 8 步 · 打开网页，开始抠图

引导结束会自动启动服务，终端最后会打印一个地址，通常就是：

```
http://127.0.0.1:7860
```

用浏览器打开它即可看到界面：

1. 把图片**拖进左侧上传区**（或点上传按钮 / 直接粘贴截图）；
2. 等待几秒，右侧出现**透明背景**结果；
3. 点结果图下方的下载按钮，保存透明 PNG；
4. 每张处理结果也会自动存到项目里的 `output/` 目录。

> 内存策略默认「抠完即释放」，每次抠完自动腾出内存，无需任何手动设置。

✅ 到这里部署完成，可以正常使用了。

---

## 三、以后怎么用

每次使用只需一条命令：

```bash
./run.sh
```

- **纯本地离线运行**：不再需要网络（依赖与权重都已就绪），不上传图片、不调用云端；
- **加装其它模型**：`./setup.sh`，输入新模型的编号，只补装它需要的依赖和权重；
- **补下没下完的权重**：`./download_models.sh`（可多选，如 `./download_models.sh 3,5`）。

---

## 四、常见问题（FAQ）

**Q: 提示 `Permission denied`，无法执行？**
多半是 ZIP 下载导致脚本丢了执行权限。执行 `chmod +x run.sh setup.sh download_models.sh` 后重试。

**Q: 提示 `command not found: python3`，或版本低于 3.10？**
回到第 2 步，安装 Python 3.10+ 后再来。安装引导本身也会先做版本检查并给出提示。

**Q: 下载权重很慢 / 中途失败？**
重新运行 `./setup.sh`（或 `./download_models.sh`）即可**断点续传**。国内网络可先执行：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

再重跑，会自动走 hf-mirror 镜像，通常快很多。

**Q: 终端出现「检测到本地代理」是什么？会不会上传我的图片？**
只是**首次装依赖时**探测到本机代理、用于加速从 PyPI 下载包而已。工具本身纯本地离线运行，
代码强制离线模式、只读 `models/` 目录，不上传任何图片。

**Q: 浏览器没自动弹出 / 打不开地址？**
启动成功时会自动打开默认浏览器；若没弹出，把终端里最后打印的地址（`http://127.0.0.1:7860`）手动复制到浏览器。
若终端报 `Address already in use` 之类，说明 **7860 端口已被别的程序占用**：关掉占用它的程序，
或把 `app.py` 里的 `server_port=7860` 改成别的端口（如 7861）再运行 `./run.sh`。

**Q: 想一次性装全部依赖（老方式 / 手动全装）？**
```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./download_models.sh      # 再下载需要的权重
```
（`requirements.txt` 是全量入口，会连 PyTorch 约 2 GB 一起装。）

**Q: 有 Windows 版吗？**
暂无官方 Windows 一键脚本（一键脚本基于 bash）。Windows 用户建议装
[WSL2](https://learn.microsoft.com/windows/wsl/install)（Ubuntu）后按本指南运行。

---

## 五、支持的模型（该选哪个？）

| 编号 | 引擎 | 名称 | 特点 | 权重文件 | 依赖 |
| --- | --- | --- | --- | --- | --- |
| 1 | RMBG-2.0 | 均衡全能 | BRIA 出品, 电商/通用均衡 | `models/RMBG-2.0/model.onnx` | onnxruntime |
| 2 | BEN2 | 电商友好 | 保留关联前景 | `models/BEN2/BEN2_Base.onnx` | onnxruntime |
| 3 | BiRefNet | 发丝级高精度 | 当前开源事实标准, 细节最好 | `models/BiRefNet/model.safetensors` (+3 个架构文件) | torch + transformers + timm |
| 4 | FeyNoBg | 最新 4K/8K | 八项基准四项 SOTA | `models/FeyNoBg/model.safetensors` (+config) | `nobg>=0.2.5` |
| 5 | InSPyReNet | 轻快省资源 | transparent-background 内核 | `models/InSPyReNet/ckpt_base.pth` | `transparent-background` |

**怎么选：**

- **第一次用 / 只装一个** → 选 `1` RMBG-2.0（CPU 也能跑，通用均衡）；
- **抠图要精细（头发丝、图标细节边缘）** → 加装 `3` BiRefNet 或 `4` FeyNoBg；
- **电商抠商品、想保留关联前景** → 选 `2` BEN2；
- **电脑较老 / 内存小** → 选 `5` InSPyReNet（轻快低占用）。

> Apple Silicon (M 系列) 会自动启用 MPS 加速；其余机器自动回退 CPU。

---

## 六、进阶：依赖是怎么按需省下来的

依赖按模型拆分，`setup.sh` 根据你的选择只装对应组。可用
`SETUP_DRY_RUN=1 ./setup.sh 1` 先预览（不实际安装）会执行什么：

| 依赖组 | 包含 | 何时需要 |
| --- | --- | --- |
| core (必装) | gradio / pillow / numpy | 所有模型 + Web 界面 |
| onnx | onnxruntime | 选了 RMBG-2.0 / BEN2 |
| torch | torch + torchvision (~2GB) | 选了 BiRefNet / FeyNoBg / InSPyReNet |
| birefnet | transformers / timm / einops / kornia | 选了 BiRefNet |
| (feynobg) | `nobg>=0.2.5` | 选了 FeyNoBg |
| (inspyrenet) | `transparent-background` | 选了 InSPyReNet |

缺依赖时**界面会给出对应提示**（`⚠️ 缺少…`），不影响其它引擎使用。

---

## 七、目录结构

```
.
├── app.py                # Gradio Web 界面入口
├── run.sh                # 一键启动 (无环境时自动进入 setup.sh 引导)
├── setup.sh              # 按需安装器: 选模型 → 只装所需依赖 → 下载对应权重
├── download_models.sh    # 单独补下模型权重 (多选/断点续传)
├── requirements.txt      # 全量依赖入口 (老方式/手动全装用)
├── requirements-core.txt # 依赖分组: 必装
├── requirements-onnx.txt # 依赖分组: RMBG-2.0 / BEN2
├── requirements-torch.txt# 依赖分组: PyTorch 系 (~2GB)
├── requirements-birefnet.txt  # 依赖分组: BiRefNet 专用
├── engines/
│   ├── base.py           # 引擎基类 + 注册表
│   ├── common.py         # 图像/设备工具
│   ├── onnx_engines.py   # RMBG-2.0 / BEN2 (onnxruntime)
│   └── torch_engines.py  # BiRefNet / FeyNoBg / InSPyReNet (PyTorch)
├── models/               # 模型架构文件(入库) + 权重(用 setup.sh 下载)
└── output/               # 抠图结果
```

---

## 八、内存说明（重要）

本机 18GB 内存实测：torch 系模型(MPS) 常驻约 **1~1.5 GB**，卸载后内存基本归还；
两个 CPU-ONNX 模型**瞬时峰值较高**：BEN2 ≈3.5 GB、**RMBG-2.0 ≈8 GB**（fp32 模型在 1024² 输入的中间激活所致，
推理结束、删除会话后 RSS 可能虚高，OS 会在后续内存压力下回收，非泄漏）。

因此界面默认：

- **内存策略 = 「抠完即释放」(auto)**：每次抠图完成立即释放模型内存，无需手动操作；
  内存始终低位（代价是每次都要重新加载，RMBG 加载约 3s）。
  另有「单模型驻留」「全缓存」两个选项可按需切换。
- **默认模型 = RMBG-2.0**（常用均衡款，CPU 推理约 12s）。要细节选 BiRefNet / FeyNoBg。
- 页面顶部状态面板标注了每个模型的预估内存；每次抠图后「运行信息」会显示当前进程内存占用及「已自动释放」提示。
- 说明：RMBG/BEN2 的 ONNX 运行时会把内存暂存在进程内、RSS 数字回落有滞后（实测第二次释放后即回落到 ~0.3 GB，属正常分配器行为，非泄漏）；也可手动点 **「🧹 释放已加载模型」** 或改用 torch 系模型。

---

## 九、实测性能（Apple M3 Pro, 1024×1024 输入，测试图为单物体场景）

| 引擎 | 设备 | 加载耗时 | 单图推理 | 说明 |
| --- | --- | --- | --- | --- |
| FeyNoBg | MPS | ~4s | ~1.7s | 极速且细节好 |
| BiRefNet | MPS | ~17s | ~3.8s | 精度最高，发丝级 |
| InSPyReNet | MPS | ~19s | ~3.2s | 内存友好 |
| RMBG-2.0 | CPU | ~3s | ~12s | 通用均衡 |
| BEN2 | CPU | ~0.5s | ~10s | 电商友好 |

示例输出（合成测试图与 5 个模型的实际抠图结果）保存在 `output/examples/`。

---

## 十、自检与备注

**自检**（跑全部引擎，输出 alpha 范围/耗时）：

```bash
./.venv/bin/python smoke_test.py
```

**备注：**

- 界面当前展示「耗时 + 进程内存」方便对比各模型。
- 商用前请核对各模型许可（尤其 RMBG-2.0 为 CC BY-NC 4.0 非商用；详见 `models/来源与说明.txt`）。
