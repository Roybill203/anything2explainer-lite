#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lite_gate.py —— lite 档「四轴一次跑完」收尾门禁（rc=1 即不通过）

为什么需要它：
  EXP-01 实测，C2 首版**跳过 `frame_metrics`** 就漏掉一个硬规则违反（换图元时
  `glow` 忘记传 → 220px 主角无光，而 `motion_check` 与 `selfcheck` 都不会报）。
  失败模式不是「判据错」，是「**有一根轴没跑**」——而没跑的轴不会报错。
  → 把四轴合并成一条命令 + 一个退出码，让「跳跑」在结构上不可能发生。

四轴（覆盖的物理量互不重叠，缺一不可）：
  1. selfcheck      结构与分镜一致性：帧覆盖 / GlitchIn 白名单 / 画面字面量 / [drift]   → rc 门禁
  2. zorder_audit   元素间空间冲突：层序倒置 Z1 / 同帧叠字 Z2 / **可审覆盖率**         → rc 门禁
  3. motion_check   动效密度：静止帧占比 / 最长静止                                      → 成片期，rc 门禁
  4. frame_metrics  画面构成：主体尺度 / 柔光 / 紫色碎片 / 背景碎屑                      → 成片期

分期（`--stage auto` 自动判）：
  构建期（无 fin_frames）：只能跑 1、4 中的 1 与 2 → 另两轴**显式标注「未跑」**，不算通过。
  成片期（有 fin_frames）：四轴全跑。此时若仍有轴未跑，门禁直接不通过。

用法：
  python scripts/lite_gate.py                      # 自动分期，输出 qc/lite_gate.md
  python scripts/lite_gate.py --tag v1             # 产物命名 qc/lite_gate_v1.md
  python scripts/lite_gate.py --require-final      # 强制成片期（构建期缺 frames 即失败）
  python scripts/lite_gate.py --min-coverage 85    # 放宽覆盖率（默认 90）

退出码：任一已运行轴不通过 → 1；构建期且有轴未跑 → 1（除非 --allow-partial）。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
try:
    import _env
    _env.safe_stdout()
except Exception:                                       # noqa: BLE001
    _env = None


def opt(name, default=None, cast=str):
    a = sys.argv[1:]
    if name in a and a.index(name) + 1 < len(a):
        try:
            return cast(a[a.index(name) + 1])
        except Exception:                               # noqa: BLE001
            return default
    return default


def flag(name):
    return name in sys.argv[1:]


def run(script, args, timeout=1800):
    """跑同目录下的兄弟脚本，返回 (rc, stdout)。编码问题一律降级不抛。"""
    p = os.path.join(HERE, script)
    if not os.path.isfile(p):
        return 127, f'[lite_gate] 找不到 {script}'
    try:
        r = subprocess.run([sys.executable, p] + args, cwd=ROOT,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=timeout)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except subprocess.TimeoutExpired:
        return 124, f'[lite_gate] {script} 超时（>{timeout}s）'
    except Exception as e:                              # noqa: BLE001
        return 125, f'[lite_gate] {script} 执行异常：{e}'


def read(p):
    try:
        return open(p, encoding='utf-8').read()
    except Exception:                                   # noqa: BLE001
        return ''


def main():
    shots = opt('--shots', os.path.join('src', 'shots'))
    frames = opt('--frames', 'fin_frames')
    sb = opt('--storyboard', '分镜表.md')
    stage = opt('--stage', 'auto')
    tag = opt('--tag', '')
    max_high = opt('--max-high', 0, int)
    min_cov = opt('--min-coverage', 90.0, float)
    # frame_metrics 的「高」是相对量（C0 基线本身就有 1 条空场高），默认只报告不门禁。
    # 想门禁就传一个数；传 0 表示「一条都不许有」。
    max_fm_high = opt('--max-fm-high', -1, int)
    out = opt('--out', os.path.join('qc', f'lite_gate{("_" + tag) if tag else ""}.md'))
    jout = opt('--json', '')

    fdir = os.path.join(ROOT, frames)
    n_frames = len([f for f in os.listdir(fdir)
                    if re.match(r'f_\d+\.(jpg|jpeg|png)$', f)]) if os.path.isdir(fdir) else 0
    has_frames = n_frames > 0

    if stage == 'auto':
        stage = 'final' if has_frames else 'build'
    if flag('--require-final') and not has_frames:
        stage = 'final'

    rows = []          # (轴, 命令, 读数, 判定 ok/None(未跑)/False, 详情)

    # ---- 轴 1：selfcheck（结构与分镜一致性）----
    rc, so = run('selfcheck.py', [])
    m = re.search(r'problems?[:\s]+(\d+)', so)
    sc_read = f'problems {m.group(1)}' if m else (f'rc={rc}')
    rows.append(('selfcheck', 'selfcheck.py', sc_read, rc == 0,
                 '' if rc == 0 else '有结构/一致性问题（见 stdout 或 qc 报告）'))

    # ---- 轴 2：zorder_audit（元素空间冲突 + 可审覆盖率）----
    zjson = os.path.join(ROOT, 'qc', f'zorder{("_" + tag) if tag else ""}.json')
    zmd = os.path.join(ROOT, 'qc', f'zorder{("_" + tag) if tag else ""}.md')
    os.makedirs(os.path.dirname(zmd) or '.', exist_ok=True)
    rc, so = run('zorder_audit.py', [shots, '--gate',
                                     '--max-high', str(max_high),
                                     '--min-coverage', str(min_cov),
                                     '--json', zjson, '--md', zmd])
    zt = read(zmd)
    # 优先读审计器写的 JSON（结构化）。退回到正则时**必须锚定「覆盖率」这个词**——
    # 否则会匹配到报告里任意一个 `= 12.3%`，静默给出错读数（读数错→理由错→人被骗）。
    tot, hi, cov = -1, -1, -1.0
    try:
        zj = json.loads(read(zjson))['totals']
        tot, hi, cov = int(zj['hits']), int(zj['high']), float(zj['coverage_pct'])
    except Exception:                                   # noqa: BLE001
        mh = re.search(r'合计命中\s*(\d+)\s*条（高\s*(\d+)\s*/\s*中\s*(\d+)）', zt)
        mc = re.search(r'可审覆盖率[：:][^=\n]*=\s*([\d.]+)%', zt)
        if mh:
            tot, hi = int(mh.group(1)), int(mh.group(2))
        if mc:
            cov = float(mc.group(1))
    z_ok = rc == 0
    z_read = (f'命中 {tot}（高 {hi}）/ 覆盖 {cov:.1f}%'
              if tot >= 0 and cov >= 0 else f'rc={rc}')
    z_why = []
    if z_ok is False and hi > max_high:
        z_why.append(f'层序高 {hi} 条（上限 {max_high}）→ 后出现的元素被先出现的实心块压住')
    if z_ok is False and 0 <= cov < min_cov:
        z_why.append(f'可审覆盖率 {cov:.1f}%（下限 {min_cov:.1f}%）→ 有盲区，'
                     f'"0 命中"不可信；按契约 §13 把坐标改成字面量或补 zorder_parts.json')
    rows.append(('zorder', 'zorder_audit.py --gate', z_read, z_ok, '；'.join(z_why)))

    # ---- 轴 3、4：成片期才可跑 ----
    if has_frames:
        rc, so = run('motion_check.py', ['--frames', frames])
        m = re.search(r'shots failing:\s*(\d+)', so)
        bad = int(m.group(1)) if m else -1
        rows.append(('motion', 'motion_check.py --frames', f'超限镜头 {bad} 个', bad == 0,
                     '' if bad == 0 else f'{bad} 个镜头静止率 >40% 或最长静止 >1.0s'))
        fmo = os.path.join(ROOT, 'qc', f'frame_metrics{("_" + tag) if tag else ""}.md')
        rc, so = run('frame_metrics.py', ['--frames', frames, '--storyboard', sb,
                                         '--out', fmo])
        ft = read(fmo)
        m = re.search(r'标记合计：高\s*(\d+)\s*/\s*中\s*(\d+)\s*/\s*低\s*(\d+)', ft)
        if m:
            fh, fm, fl = (int(m.group(i)) for i in (1, 2, 3))
            if max_fm_high < 0:
                f_ok = 'report'
                f_why = ('仅报告不门禁：逐条并入 QC 人工裁定'
                         '（C0 基线本身有 1 条"空场"高，"高"是相对量）')
            else:
                f_ok = fh <= max_fm_high
                f_why = '' if f_ok else f'高 {fh} > 上限 {max_fm_high}'
            f_read = f'高 {fh} / 中 {fm} / 低 {fl}'
        else:
            f_read, f_ok, f_why = '未产出报告', False, 'frame_metrics 未产出可读报告'
        rows.append(('framemetrics', 'frame_metrics.py --frames', f_read, f_ok, f_why))
    else:
        rows.append(('motion', 'motion_check.py --frames', '未跑（无 fin_frames）', 'skip',
                     '成片渲染后必跑；组级低分辨率读数偏松，成片才是判据'))
        rows.append(('framemetrics', 'frame_metrics.py --frames', '未跑（无 fin_frames）', 'skip',
                     '成片渲染后必跑'))

    # ---- 汇总 ----
    hard_fail = [r for r in rows if r[3] is False]
    not_run = [r for r in rows if r[3] == 'skip']
    allow_partial = flag('--allow-partial')
    passed = not hard_fail and (not not_run or allow_partial)
    why_final = []
    if hard_fail:
        why_final.append('不通过轴 ' + ','.join(r[0] for r in hard_fail))
    if not_run and not allow_partial:
        why_final.append('未跑轴 ' + ','.join(r[0] for r in not_run))

    L = ['=' * 76]
    L.append(f'lite 门禁 · {stage} 期 · 项目 {os.path.basename(ROOT)}'
             + (f' · tag={tag}' if tag else ''))
    L.append('=' * 76)
    L.append(f'{"轴":<14}{"读数":<30}{"判定"}')
    L.append('-' * 76)
    for name, cmd, read_s, ok, why in rows:
        if ok is True:
            mark = '✓ 通过'
        elif ok is False:
            mark = '✗ 不通过'
        elif ok == 'report':
            mark = '· 仅报告'
        else:
            mark = '⚠ 未跑'
        L.append(f'{name:<14}{read_s:<30}{mark}')
        if why:
            L.append(f'    → {why}')
    L.append('-' * 76)
    L.append(f'门禁结论：{"✓ 通过" if passed else "✗ 不通过"}'
             + (f'（{"；".join(why_final)}）' if why_final else ''))
    if not_run and not allow_partial:
        L.append('注：未跑的轴不等于通过。成片渲染完成后重跑本命令。')
    txt = '\n'.join(L)

    os.makedirs(os.path.dirname(os.path.join(ROOT, out)) or '.', exist_ok=True)
    open(os.path.join(ROOT, out), 'w', encoding='utf-8').write(txt + '\n')
    if jout:
        def _ok(v):
            if v == 'skip':
                return None
            if v == 'report':
                return 'report'
            return bool(v)
        json.dump([dict(axis=r[0], cmd=r[1], reading=r[2], ok=_ok(r[3]), why=r[4]) for r in rows],
                  open(os.path.join(ROOT, jout), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    print(txt)
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
