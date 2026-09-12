# 共用层 API（`import {…} from '../../common'`）

> 从 `src/common/*.ts(x)` 的导出抄录。common 的导出很少变；若你在源码里看到本文件没有的名字，以源码为准。
> 图形图元在 `ui.tsx` / `fx.tsx` → 见 `api-index.md`。

## 缓动与工具（`easing.ts` / `lib.tsx`）
- `clamp01(v)` · `clamp(v,lo,hi)` · `lerp(t,t0,t1,v0,v1)`
- `slideIn(n,N=22,p=2.5)` · `powOutRemain(n,N=22,p=2.5)` · `expOut(k)` · `powIn(p)` · `easeInOutPow(p=2.5)` · `easeOutCubic(t)` · `easeOutQuad(t)` · `easeInOutCubic`
- `cubicBezier(x1,y1,x2,y2)` · `BEZ_SCALE_IN`（= `cubicBezier(.1,.1,.35,1)`，21 帧缩放入场用）
- `emphasisPulse(n, {peak, up, hold, down})` · `kf(n, pairs[, ease])`（**超出末帧保持末值**）· `stepKf(n,pairs)` · `keyframes(t,kf)` · `stepHold(t,kf)`
- `rnd(...seeds)` 确定性随机（**禁 `Math.random`**）

## 字体与排版
- `FONT_HEAVY`（Noto Sans SC；标题 900、标签 600–800）· `FONT_TECH`（Exo 2 斜体，英文技术词）· `FONT_WIDE`（Audiowide，宽体大写）· `FONT_ORB`（Orbitron，数字）· `FONT_MONO` · `FONT_SERIF`（Times，公式）
- `SQUEEZE`（中文 .85 / 英文 1）· `TEXT_DY`（中文 −2 / 英文 0）—— 由 `VIDEO.lang` 自动，**不要手写死值**
- `W=1280` · `H=720` · `FPS=30`

## 组件
- `GlitchIn`（重点词 12 帧入场）：`N f0 rgbSplit slices sliceBands seq persistSplit persistSlices seed style`
  · `GLITCH_SEQ` / `GLITCH_SEQ_B`（12 帧透明度模板）· `glitchOpacity(n, seq)`
- `DirBlur`：`bx by`（方向模糊）
- `SubtitleLine` / `Subtitles` / `SUB_STYLE` / `strokeShadow`（描边字样式复用；**字幕由共用层自动渲染，镜头里不要画**）
- `Fog`：`top=415 bottom=687 from to opacity`（幕底雾；Main 常驻，组里不画）
- `StarField`：`variant count speed lifetime twinkle size brightness seed region opacity frame`
- `DotFieldBg`（点阵波幕底，`config.bg='dots'` 时由 Main 挂）
- `ProgressBar`：`dimKf frame`（覆盖层用）· `currentChapter(N)`
- `FootageTrack` / `FootageClip` / `DarkGrade`（可选实拍层）

## 类型与时间轴（`types.ts` / `timeline.ts`）
- `ShotDef{id, from, to, Comp, layer?}`（`layer: 'aboveBar'` 表示画在进度条之上）
- `BgSpec{from, to, fog?, stars?}`（幕底覆写；`fog:false stars:'none'` = 纯黑无星）
- `TOTAL_FRAMES` · `CHAPTER_STARTS` · `SENTENCES`（由 `tts_build.py` 生成，**不要手改**）
