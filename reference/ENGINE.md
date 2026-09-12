# 引擎与独立性（ENGINE）

> **本 skill 是完全独立的：下载即用，不需要安装 `anything2explainer` 主 skill。**
> 引擎（Remotion 模板）、示例资产、参考文档、门禁脚本**全部自带**。

---

## 1. 自带件清单

| 路径 | 内容 | 体量 |
|---|---|---|
| `template/` | **Remotion 4 + React 19 + TS 引擎**（`src/` 图元·光效·覆盖层·共用层，`scripts/` 22 个工具，`public/fonts/` 四款字体 + OFL 许可） | 17.61 MB（字体占 16.95 MB） |
| `examples/rag/` | 样片全套：`shots_src/`（81 个文件，§11 模式路由的落点）、`frames/`（参考帧 = 质量标尺）、`research.md`、`storyboard_src.md`、`分镜表.md`、`timeline.md`、`qc/` | 3.84 MB |
| `examples/contrast/` | 6 组正/反例对照 + `contrast_sheet.jpg` | 0.99 MB |
| `reference/` | 协议文档（见 §4） | 0.17 MB |
| `LICENSE` · `NOTICE` · `CITATION.cff` | **上游授权、再分发通告与改动声明、引用信息**（模板内含 OFL 字体，务必随包保留） | — |
| `README.md` / `README_zh.md` | **本档自己的说明**（英文为主，中文副） | — |
| `UPSTREAM_README.md` / `UPSTREAM_README_zh.md` | **上游 README 原样存档**（描述的是完整版布局，不是本仓库） | — |
| `WINDOWS-PORT.md` | Windows 移植说明（上游 zsh/rsync → 本档 .py） | — |

**合计约 22.6 MB。** 其中 17 MB 是那 4 款字体 —— **不要为了瘦身删掉**：缺字体则 `zorder_audit.py` 的墨迹实测量尺退化为启发式估宽，§12 的卡位判定会失准。

---

## 2. 起项目：一条命令

```bash
python <本skill>/scripts/lite_bootstrap.py <目标目录> <slug>
```

做四件事：

1. **前置检查** —— 校验自带引擎 17 个关键件 + 4 份协议文档 + 10 项软资产；**缺件早失败**（不会跑到一半才发现）
2. 跑自带引擎的 `template/scripts/new_project.py <目标目录> <slug>`（复制模板 → `npm install` → `tsc --noEmit`）
3. 把 `build-contract-lite.md` / `qc-lite.md` / `prompts-lite.md` / `lessons-lite.md` 拷进项目的 `reference/`
4. 生成 `reference/api-index.md`（图元签名索引，ui+fx 15.6K → 1.3K）

**开关**：`--skip-install`（只复制，调试用）· `--no-api-index`（跳过索引生成）· **`--check`（只做独立性自检，不建项目）**。

```bash
# 确认安装是否完整（不需要任何外部依赖）：
python <本skill>/scripts/lite_bootstrap.py --check
# → [lite] 引擎来源：本 skill 自带  →  ...\anything2explainer-lite\template
# → [lite] 自带件检查：✓ 全部就位
# → [lite] 独立性自检通过 ✓
```

**为什么 `template/scripts/` 里的脚本能自定位**：`_env.package_root()` 取「脚本所在目录的上级」并校验 `src/config.ts` 与 `src/common/` 存在。所以引擎无论被放在哪个 skill 目录下都能正确工作 —— **这就是本 skill 能自带引擎的前提**。

可选覆盖：`set A2E_ENGINE=<template 目录>` 可改用外部引擎，**仅用于开发期对比调试**，正常使用不要设。

---

## 3. 门禁脚本住在引擎里（有意为之）

`zorder_audit.py` 与 `lite_gate.py` 放在 **`template/scripts/`**，不是 `scripts/`。原因：

`new_project.py` 会**连 `scripts/` 一起复制**到新项目 → 项目一建好就自带这两道门禁，不需要再分发。而 `lite_gate.py` 是以**兄弟进程**方式调用同目录脚本（`run('selfcheck.py', ...)`），它必须和 `selfcheck.py` / `motion_check.py` / `frame_metrics.py` 在同一个 `scripts/` 里。

→ **不要**在 `anything2explainer-lite/scripts/` 下再放一份副本（会与项目里的版本漂移）。

`anything2explainer-lite/scripts/` 里**只有** `lite_bootstrap.py` 一个文件，那是"建项目"用的，不进项目。

---

## 4. 参考文档分工（**别读错**）

| 文档 | 什么时候读 |
|---|---|
| `build-contract-lite.md` | **构建组必读**（硬约束全集 + §12/§13/§14）。派单时附上 |
| `qc-lite.md` | 主会话收尾（四轴门禁、回退判据、覆盖矩阵、人工审片清单） |
| `prompts-lite.md` | 派单模板（构建 / 修复 / 终检） |
| `lessons-lite.md` | **必读教训摘录**（遮挡类优先，A–E 五组） |
| `style-guide.md` | 阶段 3–4（画风 / 安全区 / 调色板 / 图元目录） |
| `motion-vocabulary.md` | 阶段 3（动效帧数、运镜预算、闪烁白名单） |
| `composition-and-light.md` | 阶段 3（主体尺寸三档、光跟主角、高光时刻、§7 持续动作判据） |
| `narration-storyboard.md` | 阶段 2（解说词 / 配音参数 / 字幕切块 / 分镜令牌） |
| `research-brief.md` | 阶段 1（研究员 prompt 与事实规则） |
| `common-api.md` | 查共用层 API（图形图元见项目里生成的 `api-index.md`） |
| `prompts.md` | **仅参考其「研究 / QC / 复验」段落**；构建与修复派单**一律用 `prompts-lite.md`**（`prompts.md` 是完整版的 C0 语义，含"每镜 ≥6 张图"这类与本档冲突的要求） |
| `lessons.md` | 完整版教训累积（72 K）。`lessons-lite.md` 是必读摘录；本档新教训**追加到 `lessons.md` 末尾** |

**本 skill 有意不含**（完整版独有，与 lite 的低成本前提冲突）：
`agent-build-rules.md`（12 K，C0 语义）、`agent-qc-rules.md`（C0 三轮 QC）、`build-contract.md`（未瘦身版，等价物是 `build-contract-lite.md`）、`api-index.md`（按项目生成，见 §2 第 4 步）。

---

## 5. 维护：与原 skill 的同步关系（**只有维护者需要看**）

本 skill 的 `template/` / `examples/` / 8 份通用 reference 是**从 `anything2explainer` 出来的副本**（上游授权 PolyForm Noncommercial 1.0.0，见根目录 `LICENSE` / `NOTICE`）。原 skill 更新时，同步以下内容即可（**不要反向覆盖本 skill 的 `*-lite.md`，也不要用上游 README 覆盖本档自己的 `README.md`**）：

```powershell
# $S = 上游检出目录（git clone https://github.com/Vincentwei1021/anything2explainer）
# $D = 本 skill 根目录（把下面的路径换成你自己的）
$S = "<你的上游检出目录>"
$D = "<本 skill 根目录>"

# 引擎与示例（整体覆盖；注意别覆盖本档新增的两道门禁：
#   template/scripts/zorder_audit.py、template/scripts/lite_gate.py）
Copy-Item "$S\template" "$D\template" -Recurse -Force
Copy-Item "$S\examples" "$D\examples" -Recurse -Force

# 通用参考文档（只同步这 8 份；本档的 *-lite.md 不动）
foreach($f in @("style-guide.md","motion-vocabulary.md","composition-and-light.md",
                "narration-storyboard.md","research-brief.md","prompts.md",
                "common-api.md","lessons.md")){
  Copy-Item "$S\reference\$f" "$D\reference\$f" -Force
}

# 授权与引用 —— 只同步这三样
foreach($f in @("LICENSE","CITATION.cff")){ Copy-Item "$S\$f" "$D\$f" -Force }

# 上游 README 只进存档位（绝不要写成 $D\README.md）
Copy-Item "$S\README.md"    "$D\UPSTREAM_README.md"    -Force
Copy-Item "$S\README_ZH.md" "$D\UPSTREAM_README_zh.md" -Force
```

**本 skill 独有、不要被覆盖**：`SKILL.md` · `README.md` / `README_zh.md` · `NOTICE` · `WINDOWS-PORT.md` · `scripts/lite_bootstrap.py` · `reference/{build-contract-lite.md, qc-lite.md, prompts-lite.md, lessons-lite.md, ENGINE.md}` · `template/scripts/{zorder_audit.py, lite_gate.py}`。

**已对引擎做的两处文档级修补（同步后需重新施加）** —— 原始 docstring 引用了本 skill 未打包的 C0 文件：

| 文件 | 原本 | 改为 |
|---|---|---|
| `template/scripts/frame_metrics.py` 文件头 | `（配 composition-and-light.md §6 与 agent-qc-rules.md）` | `（配 composition-and-light.md §6）` |
| `template/scripts/zorder_audit.py` 文件头 | `（… / agent-build-rules §2）` | `（build-contract-lite.md §12 层序纪律 / composition-and-light.md §4 空间安全）` |

两处都只是 docstring，**不影响脚本行为**；但留成悬空引用会让读代码的人去找一个不存在的文件。

同步后跑一次 `python scripts/lite_bootstrap.py --check` 确认完整性。

**漂移风险表**

| 引擎里的东西 | 影响 | 应对 |
|---|---|---|
| `template/src/**`（图元、光效、覆盖层） | 改图元 → `api-index.md` 过时 | 重跑 `gen_api_index.py`（每个项目各跑一次），协议不用改 |
| `template/scripts/*.py` | 接口变了 | 同步本 skill 的 `prompts-lite.md` / `qc-lite.md` |
| `template/scripts/zorder_audit.py` | 判据变了 | 同步 `build-contract-lite.md` §12–§14 |
| `template/public/fonts/**` | **墨迹宽度变了 → §12 的卡位要全部重算** | 慎换字体 |
| `template/public/fonts/LICENSE.md` + 根 `LICENSE`/`CITATION.cff` | 授权与引用 | **不要删** |

---

## 6. 环境前置（Windows）

- **不要用 `python3`** —— Windows 下可能解析到 Microsoft Store 占位程序。请用你自己的 venv 解释器，
  或把它的绝对路径写进环境变量 **`A2E_PYTHON`**（5 个 `.sh` 会优先采用；也可直接调同名 `.py`）。
  需要的第三方包：`numpy` / `pillow` / `scipy` / `edge-tts`。
- 同理，Node 找不到时用 **`A2E_NODE`** 指定（`template/scripts/_env.py` 的 `exe()` 会先读环境变量，再查 PATH，最后退回系统默认安装目录）。
- **项目放短路径**（如 `D:/a2e/<slug>`）—— `node_modules` 嵌套很深，路径过长会撞 Windows 260 字符 MAX_PATH。
- 国内网络建议自行配镜像（npm → npmmirror，pip → 清华源）。
- 磁盘约 **2 GB/片**（`node_modules` + 渲染帧），开工前留 ≥5 GB。

---

## 7. 旧坑（别再踩）

1. **MSYS 路径**：`os.path.abspath('/d/a2e/x')` 在 Windows 上变成 `D:/d/a2e/x` —— **静默进错目录**。凡脚本接收命令行路径，先过 `_env.winpath()`（`lite_bootstrap.py` 内置同款 `winpath()`）。
2. **`nb_frames`**：`ffprobe` 不带 `-select_streams v:0` 会被**音频流**覆盖（实测音频 2965 帧 vs 视频 1896 帧），差点误判成片规格。
3. **PowerShell 管道解码**：`& python ... | Out-File` 时 python 的 UTF-8 字节会被控制台按 GBK 解码 → 中文全乱码、日志被判成 binary。规矩：**让脚本自己写 UTF-8 文件，stdout 只做降级字符**（`_env.safe_stdout()` 已处理）。
