# Windows 移植说明 / Windows port notes

本副本在上游 [Vincentwei1021/anything2explainer](https://github.com/Vincentwei1021/anything2explainer) 的基础上做了 **Windows 适配**。
上游 README 注明「在 macOS 上开发与验证；Linux 应可用，**Windows 未测试**」，以下改动让它在 Windows（Git Bash / PowerShell）下可用。

移植日期：2026-09-11 · 上游版本：`5544f59`

---

## 一、环境要求（不再硬编码任何路径）

| 组件 | 要求 | 说明 |
|---|---|---|
| Node | **≥ 18**（实测 22.22.2） | `npx` / `npm` 必须是可解析的真实路径 |
| Python | **≥ 3.8**（实测 3.13） | 依赖：`numpy`、`pillow`、`scipy`、`edge-tts` |
| ffmpeg | 任意近期版本（实测 9.0） | 需在 PATH 中，或用 `A2E_FFMPEG` 指定 |
| 磁盘 | **≥ 5 GB** | `node_modules` + 渲染帧约 2 GB/片 |

**路径解析不再硬编码**：所有脚本走 `template/scripts/_env.py` 的 `exe()` ——
先读环境变量（`A2E_PYTHON` / `A2E_NODE` / `A2E_FFMPEG` / `A2E_NPX` …），
再查 `PATH`，最后退回系统默认安装目录。`.sh` 兼容入口优先采用 `$A2E_PYTHON`。

```bash
# 可移植写法：按需指定，不写死
export A2E_PYTHON="/path/to/your/venv/Scripts/python.exe"   # Windows
export A2E_PYTHON="$HOME/.venv/a2e/bin/python"              # macOS / Linux
```

---

## 二、改了什么

上游 5 个 shell 脚本全是 `#!/bin/zsh`，且用到 `rsync`、BSD 系 `sed -i ''`、zsh 专有数组
`${(s:,:)FRAMES}`、`mktemp -t`、`find $TMPDIR` —— 这些在 Git Bash 下**逐条失效**，不是"可能有问题"。

处理办法：**保留原文件名当兼容入口，实际实现改为同目录的 `.py`**。
这样 `SKILL.md` 与 `reference/*.md` 里记录的调用方式（`scripts/still.sh Gn ...`）**完全不用改**。

| 原文件（zsh） | 现在 | 说明 |
|---|---|---|
| `new_project.sh` | → `new_project.py` | `rsync` → `shutil.copytree`；`sed -i ''` → Python 重写 `config.ts` |
| `preview.sh` | → `preview.py` | 前 N 秒样片 |
| `render.sh` | → `render.py` | 整片渲染 + 抽帧 + contact sheet |
| `still.sh` | → `still.py` | 出 still；zsh 数组切分 → `str.split(',')` |
| `test_render.sh` | → `test_render.py` | 30 帧测渲；`mktemp -t` → `tempfile.mkdtemp` |
| —（新增） | `_env.py` | 公共层：可执行文件解析 + 路径归一 + 编码兜底 |

另外对上游 Python 脚本做了两处**最小侵入**修补：

1. **`motion_check.py`：`npx` 解析**（硬 bug，Windows 上必挂）
   上游写 `subprocess.run(['npx', ...])`。Windows 上 `npx` 实为 `npx.CMD`，
   `CreateProcess` 不认，会抛 `FileNotFoundError [WinError 2]`（已实测）。
   改为 `_env.run([_env.exe('npx'), ...])`。
2. **控制台编码兜底**：`selfcheck.py` 打印 `✗`、`tts_build.py` 打印 `⚠`，
   这些符号不在 cp936 字符集里，默认 stdout 会抛 `UnicodeEncodeError` 直接中断。
   统一在各脚本顶部加 `_env.safe_stdout()`（把编码错误降级为替换字符，保留中文可读）。

---

## 三、Windows 上的三个已知坑

### 1. 路径长度（MAX_PATH）

`node_modules` 嵌套很深，项目路径过长会触发 260 字符限制，导致安装 / 构建失败。
**建议项目放在盘根附近的短路径**，例如 `D:\a2e\my-video` 而不是深层目录。
`new_project.py` 在目标路径超过 90 字符时会打印警告。

### 2. 不要直接用系统 `python3`

Windows 下 `python3` 可能是 Microsoft Store 的占位程序（会弹商店窗口）。
手动调 Python 工具时请用 venv 的 full path，或先设 `A2E_PYTHON`。

### 3. 中文输出乱码

Git Bash 一般正常。若在 PowerShell / CMD 里看到乱码，先 `chcp 65001`；
脚本已设 `PYTHONUTF8=1`，不会因此中断，只会显示替换字符。

---

## 四、等价的调用方式

```bash
# 建项目（约 2 GB/片，建议放短路径）
scripts/new_project.sh D:/a2e/my-video myslug

# 出 still（帧号 1 起、逗号分隔、输出目录用绝对路径）
scripts/still.sh Overlay 40,120,300 D:/a2e/my-video/stills/ov ov
scripts/still.sh G1 118,140,180 D:/a2e/my-video/stills/G1 g1

# 30 帧测渲（看 fps，正常 3–12 s）
scripts/test_render.sh G1 118 g1

# 前 30 秒样片（确认点 4）
scripts/preview.sh 30

# 整片渲染
VER=v1 scripts/render.sh

# 纯 Python 工具
"$A2E_PYTHON" scripts/tts_build.py
"$A2E_PYTHON" scripts/frame_metrics.py --out qc/frame_metrics_v1.md
"$A2E_PYTHON" scripts/motion_check.py G3
"$A2E_PYTHON" scripts/selfcheck.py
```

`.sh` 与 `.py` 等价，推荐手动时直接用 `.py`（不依赖 bash）：

```bash
python D:/a2e/my-video/scripts/still.py G1 118 D:/a2e/my-video/stills/G1 g1
```

---

## 五、与上游同步

```bash
# 把上游拉到一个独立目录，然后比对
git clone https://github.com/Vincentwei1021/anything2explainer.git upstream
cd upstream && git pull

# 只同步非 scripts 部分；template/scripts/ 保留本档的移植版
# 本档 reference/ENGINE.md §5 有维护者用的同步脚本
```

**移植改动集中在 `template/scripts/`（5 个 `.sh` + 5 个 `.py` + `_env.py`）**，
其余目录保持上游原样，因此同步冲突面很小。

> 注意：`template/scripts/` 里同时有 `zorder_audit.py` 与 `lite_gate.py` 两个**本档新增**的门禁脚本，
> 同步上游时不要覆盖它们。

---

## 六、尚未验证（诚实声明）

- 完整跑一条片子的全流程（需要真实选题 + 小时级构建）
- `edge-tts` 在受限网络环境下到微软语音端点的连通性（需真实文案才能测）
- 多 agent 并行构建时 Windows 下无 tmux/pane，建议改为**分波派发**（上游按 macOS 写的）

**网络行为披露**：本 skill 唯一的对外网络行为是 `edge-tts` 调用微软语音接口，以及
`npm install` 拉取 Remotion。无凭据读取、无数据外传、无代码混淆，二进制文件均为真实字体。
