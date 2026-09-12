# 派单模板（lite 档）

> lite 档派单只有三类 agent：**构建组**、**修复组**、**终检**。
> 所有派单都必须附上：本文件对应的模板 + `reference/build-contract-lite.md`。
> **不要引入 C0 语义的构建规则**（完整版的 `agent-build-rules.md` 要求每镜 ≥6 张全尺寸图，与本档"少看图"直接冲突，因此**未打包**）。

---

## 0. 派单前主会话要准备好的东西（一次性）

```bash
# 1) 图元 API 签名索引（源码改动后重跑）
python scripts/gen_api_index.py <项目根> --out reference/api-index.md --budget 1500

# 2) 按组切片（每组一次，只抽不写）
python scripts/slice.py <项目根> --group Gn
```

派单**只给**这 6 份（合计 8.8–9.3K tok，相对 C0 的 39.1K 降 76–78%）：

| # | 文件 | 作用 |
|---|---|---|
| 1 | `reference/build-contract-lite.md` | 硬约束全集（含 §12–§14） |
| 2 | `reference/api-index.md` | 图元 props / 常量 / 帧工具签名 |
| 3 | `common/types.ts` | 类型事实（`ShotDef` / `BgSpec`） |
| 4 | `storyboard_Gn.md` | 本组分镜 |
| 5 | `timeline_Gn.md` | 本组节拍帧 |
| 6 | `facts_Gn.md` | 本组事实清单 |

**另加一句**：把上一组已验收的 `BUILD_NOTES.md` 里那张**镜头表**给新组当样例（不是给源码，是给"交付格式长什么样"）。

---

## 1. 构建组（G1–Gn，每组 5–7 镜头）

```
你是 anything2explainer-lite 的构建组 agent，负责第 <n> 组（<SCxx>–<SCyy>），共 <k> 个镜头。

【必读】按顺序读完这 6 份，读完再动手：
  1. reference/build-contract-lite.md   ← 硬约束全集；§12/§13/§14 是本档新增，务必照做
  2. reference/api-index.md             ← 图元签名；需要细节时再读对应的 ui.tsx / fx.tsx 段落
  3. src/common/types.ts
  4. script/storyboard_G<n>.md
  5. script/timeline_G<n>.md
  6. research/facts_G<n>.md

【附加样例】src/shots/G<n-1>/BUILD_NOTES.md 的镜头表 —— 你最终要交一张同样格式的表。

【范围】只改 src/shots/G<n>/**（SCxx.tsx / index.ts / 可能的 g<n>parts.tsx）。
       不改 Main / Root / common / overlay / 其它组。共用层有建议写进 BUILD_NOTES.md 并提出。

【画法】按 build-contract-lite.md §11 的模式路由表选参考源码，读**本组用到的每种模式**的参考实现。

【三条本档新增硬规范（违反即打回）】
  §12 层序纪律：入场序 = 绘制序。若 A 入场帧 < B 入场帧，A 必须写在 B 之前。
       实心容器（PaperCard / MsgCard / Envelope / PillCell / TagBlock / MiniPill / ClientBox / 非透明 Box）
       与任何**入场更晚**的元素在外扩区（含柔光）不得相交。
       确需叠放时：被压方入场帧必须 ≤ 施压方，并在 BUILD_NOTES 写明「X 有意压在 Y 上 + 理由」。
  §13 坐标须字面量：内容元素的矩形必须可由源码字面量或 const 求得。
       禁止 x={someFn()} / cx={MAP[i].cx} / 把坐标拆到外层 wrapper、内层写 x={0} y={0}。
       自定义共用件登记到 <项目根>/zorder_parts.json。
  §14 自检与交付补列：见下。

【每镜头自检（收组前每个镜头都要过）】
  a) npx tsc --noEmit 通过
  b) 出 2 张 still（入场完成帧 + 关键帧），尺度 0.25，输出 stills/G<n>/
     只用 scripts/still.sh G<n> <帧号> <绝对路径> g<n>（tag 固定 g<n）；禁用 npx remotion still
  c) python scripts/motion_check.py G<n>   → 每镜头静止 ≤40%、最长静止 ≤0.7s（构建目标）
  d) python scripts/zorder_audit.py src/shots --gate
     本组的层序命中必须为 0；若不通过，先修再交（修法见 §12）
  e) 组界帧各 1 张 → stills/G<n>/boundary_*.png

【看图纪律（本档核心）】
  只在**收组前看一次**（4 张图），看完立刻写结论、之后只引结论。
  看图只查这 5 件：文字是否被字幕带/进度条/HUD 遮挡 · 是否溢出画布 ·
  颜色是否合调色板 · 英文拼写 · 主角墨迹高度 ≥170px 且有光。
  ⚠ 缺失的几何事实**不要靠看图补**，去改源码里的数字（§13）。

【BUILD_NOTES.md 必交】
  镜头表（id/帧/文件/内容/主角/主角高度/主角的光/是否高光/运镜/配角数/
          motion_check 静止%·最长静止/**主体墨迹盒**/**最大重叠**/**Z1·Z2 命中数**）
  复用图元 · 关键参数 · 测渲耗时 · 自检发现 · 未完成项 · 对共用层的建议
  收组结论必须显式写：层序命中 高N/中M · 可审覆盖率 P% · 未解析清单（为空写"无"）

【交付】边做边写盘（每 1–2 个镜头更新 index.ts 与 BUILD_NOTES.md），不要攒到最后。
  最终回复只报：完成镜头数 · tsc 结果 · 测渲 fps · still 目录 · 层序命中/覆盖率 ·
  需主会话决定的事项。不要复述画面内容。
```

---

## 2. 修复组（一个 agent 只修一到两组）

```
你是 anything2explainer-lite 的修复组 agent，负责修复 <组/镜头清单>。

【输入】qc/qc_<tag>.md 的问题清单（已按严重度排序）+ qc/zorder_<tag>.md 的层序命中
      + reference/build-contract-lite.md（重点 §12 层序纪律）

【纪律】
- 只修清单里的条目，**不顺手优化**别的地方（会引入新问题、也会让复验无法归因）。
- 每修一条，回复里写：问题 → 改动（文件:行 + 前值→后值）→ 复验命令 → 读数。
- **改几何后必须重跑 `zorder_audit.py src/shots --gate`**——挪开一个元素可能把它压到另一个元素上。

【§12 类问题（遮挡/层序）的修法，按优先级】
  1) 把施压方（后入场的实心块）挪开：按审计给出的重叠像素数**加 ≥8px 余量**再移。
     ⚠ 不要照抄别处的历史坐标——字距/字号变了墨迹宽度就变（实测 908 vs 919）。
  2) 或把施压方的入场帧**提前**到被压方之前（顺序就对了）。
  3) 都不行 → 缩窄施压方，或把它改成半透明/描边式（并写进 BUILD_NOTES 说明）。

【复验（必交）】
  npx tsc --noEmit · motion_check.py <组> · zorder_audit.py src/shots --gate
  并给出**修复前/后**的读数对照。
```

---

## 3. 终检（成片期，主会话自己跑，不派 agent）

```bash
npx tsc --noEmit
VER=<tag> scripts/render.sh          # → renders/<slug>_<tag>.mp4 + fin_frames/
python scripts/lite_gate.py --tag <tag> --require-final
```

`lite_gate` 会给四轴读数表 + rc。**rc=1 就不要进入交付**——按 `qc-lite.md` §3 的预注册判据决定修还是回退。

终检后主会话自己做的三件（机器做不到）：

1. 拼 6 张 overview contact sheet，**核对焦点唯一性**（每帧是否只有一个视觉焦点）。
2. 按 `qc-lite.md` §6 看**节拍感 / 音画同步 / 字幕可读性**。
3. 填 `qc-lite.md` §4 的**覆盖矩阵**，把"未验证项"写进 QC 报告第 6 节。

---

## 4. 成本纪律（派单时不要忘）

- **一张图看两次 = 看两张新图。** 看图集中在生命周期尾部，看完写结论，之后引结论。
- **不要给 agent 全量 reference**——它会把 13.2K 读一遍，把省下的成本又花回去。
- **`mc_one.py` 是调单个镜头动效的唯一正确工具**（`--reuse` 复用 bundle ≈11s），不要为改一个镜头反复整片重渲。
- 派单里的 each-agent 图像预算：**构建期 ≤4 张/组（0.25 尺度）**；只有要确认文字时才出 1 张全尺寸。
