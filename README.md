# 🖼️ 本地 AI 抠图工具

纯本地运行的 AI 背景移除工具：图片**不上传任何服务器**，5 个开源抠图模型可切换，
带中文 Web 界面，支持拖拽 / 粘贴图片，一键输出透明背景 PNG。

> 模型权重来自 `models/` 目录（来源与协议见 `models/来源与说明.txt`）。

## 快速开始

首次使用（需联网一次）：
```bash
./run.sh
```
会进入**按需安装引导** `setup.sh`：

1. 列出 5 个模型，选你要用的（多选如 `1,3`，`a` 全装，`q` 退出）；
2. 只安装所选模型**需要的那部分依赖**——只选 RMBG-2.0 / BEN2 就只需轻量 onnxruntime，**不用装 torch（约 2GB）**；
3. 自动下载对应模型权重（已存在的自动跳过，支持断点续传）；
4. 装完直接启动，浏览器打开 <http://127.0.0.1:7860>。

之后每次 `./run.sh` 都是纯本地直接启动，**断网可用**。

> **想补装其它模型**？随时运行 `./setup.sh`（或 `./setup.sh 3` 直接指定编号），
> 只会补装新模型需要的依赖与权重，已装好的自动跳过。

> **模型权重不随仓库分发**：每个权重 >100MB，超出 GitHub 单文件 100MB 上限，
> 需现场下载（上面的引导即在做这件事）。只想补下权重也可用 `./download_models.sh`，见下文。

> **关于「代理」**：终端里出现的 `检测到本地代理` 只发生在**首次安装依赖**时
> （`pip` 从 PyPI 下载包走本地代理加速，见 `setup.sh`）。依赖装完后工具**纯本地离线运行**——
> 代码强制 `HF_HUB_OFFLINE` 且只读 `models/` 目录，不上传图片、不调用云端、**断网可用**
> （已用封禁网络连接的方式实测 BiRefNet / FeyNoBg / RMBG-2.0 均可正常抠图）。

## 支持的模型

| 引擎 | 名称 | 特点 | 权重文件 | 依赖 |
| --- | --- | --- | --- | --- |
| BiRefNet | 发丝级高精度 | 当前开源事实标准, 细节最好 | `models/BiRefNet/model.safetensors` (+3 个架构文件) | torch + transformers + timm |
| FeyNoBg | 最新 4K/8K | 八项基准四项 SOTA | `models/FeyNoBg/model.safetensors` (+config) | `nobg>=0.2.5` |
| RMBG-2.0 | 均衡全能 | BRIA 出品, 电商/通用均衡 | `models/RMBG-2.0/model.onnx` | onnxruntime |
| BEN2 | 电商友好 | 保留关联前景 | `models/BEN2/BEN2_Base.onnx` | onnxruntime |
| InSPyReNet | 轻快省资源 | transparent-background 内核 | `models/InSPyReNet/ckpt_base.pth` | `transparent-background` |

> Apple Silicon (M 系列) 会自动启用 MPS 加速；其余机器回退 CPU。

## 按需安装原理（依赖是怎么省下来的）

依赖按模型拆分，`setup.sh` 根据你的选择只装对应组（`./setup.sh` 可加 `SETUP_DRY_RUN=1` 预览要装什么）：

| 依赖组 | 包含 | 何时需要 |
| --- | --- | --- |
| core (必装) | gradio / pillow / numpy | 所有模型 + Web 界面 |
| onnx | onnxruntime | 选了 RMBG-2.0 / BEN2 |
| torch | torch + torchvision (~2GB) | 选了 BiRefNet / FeyNoBg / InSPyReNet |
| birefnet | transformers / timm / einops / kornia | 选了 BiRefNet |
| (feynobg) | `nobg>=0.2.5` | 选了 FeyNoBg |
| (inspyrenet) | `transparent-background` | 选了 InSPyReNet |

缺依赖时**界面会给出对应提示**（`⚠️ 缺少…`），不影响其它引擎使用。

## 只想补下权重 / 各模型大小

```bash
./download_models.sh          # 交互选择: 输入 1,3,5 可多选 / a 全下 / q 退出
./download_models.sh 1,3      # 或直接带编号参数（空格或逗号分隔）
```

> 只下 1~2 个就能用：常用 `RMBG-2.0` 或轻快的 `InSPyReNet`，要细节再加 `BiRefNet`/`FeyNoBg`。
> 国内网络下载慢时：脚本会自动尝试 hf-mirror.com 镜像与本机代理；也可 `export HF_ENDPOINT=https://hf-mirror.com` 提速。
> 直接 `./run.sh` 在检测到没有任何权重时也会自动进入上面的下载引导。

## 首次使用

最省事的方式是 `./run.sh` → 选模型 → `setup.sh` 自动完成"装依赖 + 下权重"两步，
无需手动操作。若你是老用户已装好全量依赖，或想手动安装全部依赖，可跳过 `setup.sh`：

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt   # 全量
./download_models.sh      # 再手动下需要的权重
```

## 目录结构

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

## 内存说明（重要）

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

## 备注

- 界面当前展示「耗时 + 进程内存」方便对比各模型。
- 商用前请核对各模型许可（尤其 RMBG-2.0 为 CC BY-NC 4.0 非商用；详见 `models/来源与说明.txt`）。

## 实测性能（Apple M3 Pro, 1024×1024 输入，测试图为单物体场景）

| 引擎 | 设备 | 加载耗时 | 单图推理 | 说明 |
| --- | --- | --- | --- | --- |
| FeyNoBg | MPS | ~4s | ~1.7s | 极速且细节好 |
| BiRefNet | MPS | ~17s | ~3.8s | 精度最高，发丝级 |
| InSPyReNet | MPS | ~19s | ~3.2s | 内存友好 |
| RMBG-2.0 | CPU | ~3s | ~12s | 通用均衡 |
| BEN2 | CPU | ~0.5s | ~10s | 电商友好 |

示例输出（合成测试图与 5 个模型的实际抠图结果）保存在 `output/examples/`。

## 自检

```bash
./.venv/bin/python smoke_test.py
```
会用一张内置测试图依次跑全部引擎，输出每个的 alpha 范围、不透明占比、加载与推理耗时。
