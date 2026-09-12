#!/usr/bin/env python3
"""单镜头动效快速迭代台：只渲一个合成（composition）的指定帧区间，按 motion_check 同口径出读数。

用法：
    python scripts/mc_one.py G3 1155 1254            # 首次：建 bundle + 渲染 + 出读数
    python scripts/mc_one.py G3 1155 1254 --reuse    # 复用上次 bundle（源码未改时）
    python scripts/mc_one.py G3 1155 1254 --profile  # 额外打印逐帧曲线

与 motion_check 的区别：只渲目标区间（快），且默认 step=1 出逐帧曲线，便于定位"死帧"。
判据同 §9：内容区 320×180 灰度平均变化 <0.35 记为静止帧；静止占比 ≤40% 且最长静止 ≤1.0 s。
"""
import sys, os, re, glob, subprocess, tempfile
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _env  # noqa: E402
_env.safe_stdout()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THR = 0.35

comp = sys.argv[1]
f0, f1 = int(sys.argv[2]), int(sys.argv[3])
reuse = '--reuse' in sys.argv
profile = '--profile' in sys.argv
step = 1 if profile else 3
# --scale=1 用于「像素级」核查（frame_metrics 等要 1280×720）；默认 0.5 只是为了快。
# 静止率判据不受影响：load() 一律把帧缩到 320×180 再比；只有 fullpx 诊断列会按比例变。
scale = '0.5'
for _a in sys.argv:
    if _a.startswith('--scale='):
        scale = _a.split('=', 1)[1]

sb = open(f'{ROOT}/分镜表.md', encoding='utf-8').read()
shots = [(m.group(1), int(m.group(2)), int(m.group(3)))
         for m in re.finditer(r'^\| (SC\d\d)[^|]*\| (\d+)–(\d+) \|', sb, re.M)]

# —— bundle：--reuse 时找最近的 build_dev_mc1_* ——
bundle = None
if reuse:
    cands = sorted(glob.glob(f'{ROOT}/build_dev_mc1_*'), key=os.path.getmtime)
    cands = [c for c in cands if os.path.isdir(c)]
    if cands:
        bundle = cands[-1]
        print(f'复用 bundle: {os.path.basename(bundle)}')
if not bundle:
    bundle = f'{ROOT}/build_dev_mc1_{os.getpid()}'
    print(f'新建 bundle: {os.path.basename(bundle)} ...')
    _env.run([_env.exe('npx'), 'remotion', 'bundle', 'src/index.ts',
              '--out-dir', bundle, '--log=error'], cwd=ROOT, check=True)

out = f'{ROOT}/mc_out_{comp}_{f0}_{f1}_{os.getpid()}'
os.makedirs(out, exist_ok=True)
print(f'渲染 {comp} 帧 {f0}-{f1} (scale {scale}) ...')
_env.run([_env.exe('npx'), 'remotion', 'render', bundle, comp, out, '--sequence',
          '--image-format=jpeg', '--jpeg-quality=80', f'--scale={scale}',
          f'--frames={f0 - 1}-{f1 - 1}', '--concurrency=4', '--log=error'],
         cwd=ROOT, check=True)
# 注意：Remotion `--sequence` 的产物是 element-XXXX.jpeg（不是 f_XXXX.jpg），且编号是
# **全局 0 基**帧号 —— 传 `--frames=f0-1-f1-1` 时，element-N 对应的真实帧是 **N+1**（已在
# 2026-09-11 实测确认：渲 634-1154 得到 element-633..element-1153）。
# 下面统一换算成真实帧号（`f_NNNN.jpg` 那类本来就是真实帧号，不换算）。
files = sorted(glob.glob(f'{out}/element-*.jpeg') + glob.glob(f'{out}/element-*.jpg')
               + glob.glob(f'{out}/f_*.jpg'))


def real_n(p):
    b = os.path.basename(p)
    n = int(re.search(r'(?:element|f)[-_](\d+)', b).group(1))
    return n + 1 if b.startswith('element-') else n

# 只保留可解析帧号的文件（目录里可能混入其它产物）
_bad = [f for f in files if not re.search(r'(?:element|f)[-_](\d+)', os.path.basename(f))]
if _bad:
    print('跳过非帧文件:', [os.path.basename(x) for x in _bad])
files = [f for f in files if f not in _bad]
print(f'渲染完成 {len(files)} 帧 → {os.path.basename(out)}')


def load(p):
    return np.asarray(Image.open(p).convert('L').resize((320, 180))).astype(int)[28:158, :]


def full(p):
    return np.asarray(Image.open(p).convert('L')).astype(int)


frames = [(real_n(f), load(f), full(f)) for f in files]
sampled = frames[::step]
diffs = [(sampled[i + 1][0], np.abs(sampled[i + 1][1] - sampled[i][1]).mean())
         for i in range(len(sampled) - 1)]

if profile:
    print(f'\n{"f":>5} {"mean320":>8} {"fullpx>25":>9}  bar')
    for i in range(len(frames) - 1):
        n = frames[i + 1][0]
        ms = np.abs(frames[i + 1][1] - frames[i][1]).mean()
        fp = int((np.abs(frames[i + 1][2] - frames[i][2]) > 25).sum())
        bar = '#' * min(46, int(ms * 22))
        print(f'{n:>5} {ms:8.3f} {fp:9d}  {bar}{"  <静止" if ms < THR else ""}')

print(f'\n{"shot":6s} {"len":>5s} {"still%":>7s} {"longest":>8s}  verdict   {"longest-run":>12s} {"fullpx":>8s}  class')
bad = 0
for sid, a, b in shots:
    if b < f0 or a > f1:
        continue
    dd = [(f, v) for (f, v) in diffs if a <= f <= b]
    d = [v for (_, v) in dd]
    if len(d) < 3:
        continue
    still = sum(v < THR for v in d) / len(d) * 100
    run = best = 0
    end = 0
    for i, v in enumerate(d):
        run = run + 1 if v < THR else 0
        if run > best:
            best = run
            end = i
    longest = best * step / 30
    verdict = 'OK' if still <= 40 and longest <= 1.0 else \
        ('✗ still>40%' if still > 40 else '') + (' ✗ hold>1s' if longest > 1.0 else '')
    if verdict != 'OK':
        bad += 1
    extra = ''
    if verdict != 'OK' and best > 0:
        s_ = max(a, dd[end - best + 1][0] - step)
        e_ = dd[end][0]
        idx = [i for i, (n, _, _) in enumerate(frames) if s_ <= n <= e_]
        ch = [int((np.abs(frames[i][2] - frames[i - 1][2]) > 25).sum())
              for i in idx if i > 0]
        cp = int(np.median(ch)) if ch else 0
        cls = '真静' if cp < 800 else ('小面积动作' if cp < 2500 else '有动作')
        extra = f'   {s_:>5d}-{e_:<5d} {cp:8d}  {cls}'
        lr = f'{s_}-{e_}'
    else:
        lr = ''
    print(f'{sid:6s} {(b-a+1)/30:4.1f}s {still:6.0f}% {longest:7.1f}s  {verdict:<10s} {lr:>12s} {extra}')
print(f'shots failing: {bad}')
print(f'\n[渲染帧目录] {out}')
