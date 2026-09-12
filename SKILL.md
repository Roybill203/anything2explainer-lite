---
name: anything2explainer-lite
description: 低成本档的视频讲解生产协议（anything2explainer 的 lite 版）。给一个主题，产出一条黑底 MG 风格、有配音字幕章节进度条的科普讲解视频（中文或英文，Remotion 代码动画）。相对完整版，必读清单下降约 77%（每组 39.4K → 8.8–9.3K tokens），代价是"看图能力"被压缩——因此本档用三份零图像成本的机器门禁（层序审计 / 结构自检 / 四轴合并门禁）来补偿，确保不因省成本而引入遮挡类 bug。自带完整 Remotion 引擎与示例资产（下载即用、不依赖其他 skill）。Fully self-contained — bundles its own Remotion engine, RAG sample assets, reference docs and two zero-image gates; no other skill required. Use when the user wants an explainer video but cost/token budget matters, or asks for the lite/低配/省钱 tier of anything2explainer.
agent_created: true
---

# anything2explainer-lite

**低成本档的视频讲解生产协议。自带完整引擎。** 本 skill 内含 Remotion 模板（17.6 MB）、示例资产（`examples/rag` 样片全套 + `examples/contrast` 反例）、参考文档与两道零图像门禁 —— **下载即用，不依赖任何其他 skill**。它相对完整版只替换**协议层**：读什么、出几张图、什么时候看图。

**核心取舍（先读这一段）**

| | 完整版 C0 | 本档 lite（= C2 执行方式 + §12–§14 + 四轴门禁） |
|---|---|---|
| 每组必读清单 | 39.4K tok | **8.8–9.3K（−77%）** |
| 每镜头 still | 6 张全尺寸（高光 ≥10） | **2 张 0.25 尺度（320×180）** |
| 看图时机 | 边做边看（闭环） | **生命周期尾部（开环）** |
| 视觉信号量/镜头 | 基线 | **约 1/15–1/20** |
| QC 轮数 | 3 | 3（但轴 2 是机器门禁） |

**省成本的代价是"看图能力"被压缩，而压缩会优先伤害那些"只有人眼兜底"的判据。** 所以本档不是简单地"少看图"，而是**把原本只有眼睛能发现的事变成源码里可算的数字**，再用门禁钉住：

> **能算的绝不靠看，能拦的绝不靠记。**

已实测的补偿效果：`zorder_audit.py` 在 15 个镜头上抓到 **2 条真阳性（皆"高"）、其余 14 镜零误报**，并直接给出"要移多少像素"。全片成本 −77% 的同时，运动与构图两轴**优于**完整版。

---

## 何时用 / 不用

**用**：用户要一条讲解视频，且在意时间/token 成本；或明确要"lite 档 / 低配 / 省钱版"。

**不用**（走完整版 `anything2explainer`）：
- 用户要"质量优先、不计成本"；
- 片子视觉复杂度极高、依赖大量审美微调（lite 的审美反馈环是开环的）；
- 需要与本档无覆盖的维度强相关（详见 `reference/qc-lite.md` §4 的覆盖矩阵）。

---

## 前置（Windows）

- **不要用 `python3`**（Windows 下可能解析到 Microsoft Store 占位程序）。优先用项目 venv 的解释器，或把它写进环境变量 `A2E_PYTHON` 由脚本自动使用（见 `template/scripts/*.sh`）。
- **项目放 D 盘短路径**（如 `D:/a2e/<slug>`），路径过长会撞 260 字符 MAX_PATH。
- 磁盘约 **2 GB/片**（`node_modules` + 渲染帧），开工前留 ≥5 GB。
- **引擎自带，无外部依赖。** 若要确认安装完整（不需要任何其他 skill）：

```bash
python <本skill>/scripts/lite_bootstrap.py --check
# → 引擎来源：本 skill 自带  →  ...\anything2explainer-lite\template
# → 自带件检查：✓ 全部就位
# → 独立性自检通过 ✓
```

自带件清单、维护同步说明与漂移风险见 `reference/ENGINE.md`。

---

## 流程（五阶段）

### 阶段 0 · 起项目
```bash
python <本skill>/scripts/lite_bootstrap.py <目标目录> <slug>
```
复制**自带引擎** → `npm install` → 装 lite 协议文档进项目的 `reference/` → 生成 `api-index.md`。

### 阶段 1–4 · 与完整版流程相同（**读本 skill 自带的 reference**）
调研 → 解说词与时间轴 → 分镜 → 覆盖层与图元。共 4 个确认点：**时长语言 · 文案定稿 · 配音 · 前 30 秒样片**。
按阶段读**本 skill 自己的**文档（路径都相对本 skill 根）：

| 阶段 | 读 |
|---|---|
| 1 调研 | `reference/research-brief.md` |
| 2 解说词/时间轴 | `reference/narration-storyboard.md` |
| 3 分镜 | `reference/narration-storyboard.md` + `motion-vocabulary.md` + `composition-and-light.md` + `style-guide.md` |
| 4 覆盖层与图元 | `reference/style-guide.md` + `reference/common-api.md` + `examples/rag/ui_rag.tsx` |
| 3 / 5 画法参考 | `examples/rag/shots_src/`（按 §11 模式路由表选参考源码）+ `examples/contrast/`（反例） |

> 这四阶段是**先验驱动**的（写文案、定分镜、补图元），减读清单会直接降质；**本档只压缩"构建组"的读清单与看图，不压缩这四阶段。**

### 阶段 5 · 构建组（本档与完整版差异最大的一步）

派单前主会话准备（每组一次）：
```bash
python scripts/gen_api_index.py <项目根> --out reference/api-index.md --budget 1500
python scripts/slice.py <项目根> --group Gn
```

派单只给 6 份（详见 `reference/prompts-lite.md` §0）：`build-contract-lite.md` + `api-index.md` + `common/types.ts` + `storyboard_Gn.md` + `timeline_Gn.md` + `facts_Gn.md`。

**每组收组前必跑**：
```bash
npx tsc --noEmit
python scripts/motion_check.py G<n>                  # 静止 ≤40%、最长 ≤0.7s
python scripts/zorder_audit.py src/shots --gate      # 层序命中 0 + 覆盖率 ≥90%
```

### 阶段 6 · 四轴门禁（本档的收尾关键）
```bash
VER=<tag> scripts/render.sh
python scripts/lite_gate.py --tag <tag> --require-final
```
`rc=1` 不得进入交付。四轴与判据见 `reference/qc-lite.md`。

### 阶段 7 · 交付
填 `qc-lite.md` §4 的**覆盖矩阵**（逐条标"哪条没覆盖"）+ 第 6 节**未验证项**，然后出 `交付说明.md`。

---

## 三条本档新增硬规范（**这是本档存在的理由**）

| 规范 | 一句话 | 治什么 |
|---|---|---|
| **§12 层序纪律** | 入场序 = 绘制序；实心容器不得压住后入场元素 | 「后出现的元素被先出现的块盖住」 |
| **§13 坐标须字面量** | 内容元素的矩形必须可由源码字面量求得 | 审计盲区（"0 命中"其实是瞎） |
| **§14 交付补列** | BUILD_NOTES 必填「主体墨迹盒 / 最大重叠 / Z1·Z2」 | 信息不进交付物 → 换版重建时 bug 复现 |

全文在 `reference/build-contract-lite.md` §12–§14。**这三条都是零图像成本的。**

---

## 回退判据（预注册，不许事后找理由）

触发任一即退（完整表见 `reference/qc-lite.md` §3）：

1. `zorder` 抽出 `[高]` 且完整版为 0 → **立即修**（可定点修的几何错，不必退整档），修完覆盖率 ≥90% 才可交付
2. `zorder` 可审覆盖率 **<90%** → 先补 `zorder_parts.json` / 改字面量；**覆盖率不达标时"0 命中"不可信**
3. `frame_metrics` 高 > 完整版高 且完整版为 0 → 回退
4. `frame_metrics` 中 > 完整版 + 2 → 回退
5. `motion_check` 达标率 < 完整版 − 10 个百分点 → 回退
6. 出现完整版没有的**新缺陷类型**（遮挡 / 溢出 / 节拍错位）→ 回退
7. 都不触发 且 成本降 ≥40% → **通过**

---

## 成本承诺与计账

- **必读清单**：每组 8.8–9.3K tok（实测 G1/G2/G3 = 8,833 / 9,412 / 9,301），全片 −77%。
- **图像**：构建期 ≤4 张/组（0.25 尺度），仅确认文字时出 1 张全尺寸。
- 计账：`measure.py readset --level C2 --root <项目根> --group Gn`（`measure.py` 在实验目录 `a2e-cost/`）。
- **计账坑**：分档实验把图放 `stills_C2/` 时，`scan` 默认只看 `stills/**` → **漏计**。需传 `--stills-dir stills_C2`。

**成本洞察（决定优化方向的）**：真正贵的不是图像**面积**，是**「读图后还剩多少轮」**——完整版 75 轮 vs lite 8 轮，**差 9.4 倍**。所以"在尾部定向看图"是唯一成本上说得通的看图恢复方式。

---

## 已知残留风险（**必须主动告诉用户**）

1. **审美反馈是开环的。** 构建组看不到全尺寸图，所以"细节不够完善"这类**先验驱动**的缺陷比完整版更可能残留。
2. **像素级遮挡抓不到。** `zorder_audit` 判的是**几何相交**；"柔光把邻元素洗淡"这类**像素级**问题（如大面积紫柔光在柜边形成实心环）它看不见——**这类只能用渲染期 DOM 探针或人眼，属未验证项**。
3. **覆盖率依赖代码风格配合。** 74% → 90%+ 靠 §13 的字面量纪律；不遵守纪律时，门禁会以"覆盖率不足"报错，**而不是**给你一个假的"通过"（这是刻意设计）。
4. **字幕折行 / 节奏 / 音画同步**无机器轴覆盖，必须人工审片（清单见 `reference/qc-lite.md` §6）。

---

## 关键文件

| 路径 | 作用 |
|---|---|
| `template/` | **自带引擎**：Remotion 4 项目（`src/` 图元·光效·覆盖层·共用层，`scripts/` 22 个工具含两道门禁，`public/fonts/` 4 款字体 + OFL 许可） |
| `examples/` | **自带资产**：`rag/` 样片全套（`shots_src/` 画法参考、`frames/` 质量标尺、`research.md`、`分镜表.md`）+ `contrast/` 6 组反例 |
| `scripts/lite_bootstrap.py` | 起新项目 + **独立性自检**（唯一需要手动跑的一次性命令） |
| `reference/build-contract-lite.md` | **硬约束全集**（C2 契约 + §12–§14 三条新规范）。派单必附 |
| `reference/qc-lite.md` | 四轴门禁、预注册回退判据、**覆盖矩阵**、人工审片清单 |
| `reference/prompts-lite.md` | 构建/修复/终检派单模板 |
| `reference/lessons-lite.md` | 必读教训摘录（遮挡类优先）；`reference/lessons.md` 是完整累积 |
| `reference/ENGINE.md` | **自带件清单、独立性自检、维护同步说明**、前置与旧坑 |
| `reference/{style-guide, motion-vocabulary, composition-and-light, narration-storyboard, research-brief, common-api, prompts}.md` | 阶段 1–4 的通用规范（自带副本；`prompts.md` 只取其研究/QC/复验段落） |
| `LICENSE` · `NOTICE` · `CITATION.cff` | 上游授权（PolyForm Noncommercial 1.0.0）、再分发通告与改动声明、引用信息。**请勿删除、改名或替换** |

**自带引擎侧（在 `template/scripts/`，随 `new_project.py` 自动进项目）**：
`zorder_audit.py`（层序审计门禁）· `lite_gate.py`（四轴合并门禁）·
`motion_check.py` · `selfcheck.py` · `frame_metrics.py` · `slice.py` · `gen_api_index.py`

---

## 一条要传给下一轮的方法论

**下"通过"结论前，逐条对着预注册判据标「这条由哪个轴覆盖 / 哪条完全没覆盖」；没覆盖的不许默认通过，必须写明"未验证"。**

**没覆盖比误报更危险——误报至少会响，没覆盖是无声的。**

（这条是本档诞生的直接原因：上一轮报了"通过"，而实验方案里"遮挡"这条判据既没有机器轴、也没人标注"未验证"。）

---

## 授权与再分发（**不要剥离**）

本档是上游 `anything2explainer` 的派生（上游授权 **PolyForm Noncommercial 1.0.0**）。
若你把本档复制、分发、或上传到公开仓库：

- **必须保留** `LICENSE`、`NOTICE`、`CITATION.cff` 与 `template/public/fonts/LICENSE.md`，不得删除、改名或替换。
- **不得改许可证**（不能声明为 MIT/Apache 等），不得转售、出租或再授权。非商业使用免费；**工具的商用需上游作者事前授权**（用本工具产出的视频归创作者本人）。
- **Remotion 未随包分发**：`node_modules/` 已被 `.gitignore` 排除，由使用者自行 `npm install`，并自行遵守 Remotion 自身授权（个人 / 非营利 / ≤3 人营利组织免费，见 <https://www.remotion.dev/license>）。
- 需在被分发处标注为**上游的非官方派生**。逐条改动声明见 `NOTICE` §1。
