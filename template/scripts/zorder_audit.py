#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
zorder_audit.py —— 镜头「层序冲突 / 空间占用」静态审计器（零图像 token）

为什么需要它：
  C2F 的 SC06（23.0s）把论文卡放在 x=880，压在主角「TLS 1.3」尾部 —— 而 C0 版
  同一个镜头的注释里写着「实测主角 x314-936，卡片 850-1149，重叠 86px」，并把
  卡片右移到 910 修掉了。C2F 精确复现了修复前的状态。
  → 根因不是「没看清」，是**没有任何判据在检查元素之间的空间冲突**。
  → 这类冲突是**几何问题**，源码里有字面量，可以零图像判定。

判据（对应 build-contract-lite.md §12 层序纪律 / composition-and-light.md §4 空间安全）：
  Z1 层序倒置（高）：B 在后入场（enter 更大）却排在 A 之前（被 A 压住），两者画面相交。
                     后出现的信息被先出现的东西盖住 —— 无例外地错。
  Z2 同帧叠字（中）：两个可读文本入场帧相距 <= 6 帧，墨迹盒相交 > 15%。

口径说明（重要）：
  墨迹盒 = 实际绘制的像素范围；再外扩「柔光/硬投影」半径（pad）。
  该口径经 C0 注释反向验证：HeroTLS 在 letterSpacing=0 时墨迹右缘 908.5，
  + 柔光 28px = 936.5 ≈ C0 实测的 936 ✓

可审覆盖率（本件的信任前提）：
  审计器只能审「矩形能从源码字面量求出来」的元素。求不出来的进 unresolved，
  成为**审计盲区**。盲区大时「0 命中」毫无意义 —— 实测 C0 源码上 0 命中，
  但那是假的：C0 用 wrapper 局部坐标（left:910 包 <PaperCard x={0} y={0}>）、
  主角写 cx={HERO.cx}，主角压根没参与计算。
  → 因此覆盖率是**门禁的一部分**，不是参考值。报告末尾必须给覆盖率与未解析清单。

项目级量尺表：
  <项目根>/zorder_parts.json（可选）补本项目的自定义共用件，见 reference/build-contract-lite.md §13。
  项目优先于内置表；JSON 里的 deco/texty 数组可追加「不参与遮挡判定」与「可读文本」的元件名。

用法：
  python zorder_audit.py <shots 目录> [--json out.json] [--md out.md]
  python zorder_audit.py <shots 目录> --gate [--max-high 0] [--min-coverage 90]
  字体从 <shots 目录> 往上找到的 public/fonts 读取（找不到则退回启发式估宽）。

退出码：
  默认 0（只报告）。
  --gate 下：高严重度条数 > --max-high（默认 0）或 覆盖率 < --min-coverage（默认 90）
             → rc=1；否则 rc=0。
"""
import os
import re
import sys
import json
from PIL import ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import _env                                        # noqa: E402
    _env.safe_stdout()                                 # 控制台不再因 ✓/✗/⚠ 抛编码错
except Exception:                                      # 允许把本文件单独拷出去跑
    _env = None

FX = os.environ.get('A2E_ROOT', '') or '.'          # 由 find_project_root() 在 main() 里改写
FONTS = {
    'FONT_WIDE':  'public/fonts/Audiowide-Regular.ttf',
    'FONT_ORB':   'public/fonts/Orbitron[wght].ttf',
    'FONT_TECH':  'public/fonts/Exo2-Italic.ttf',
    'FONT_HEAVY': 'public/fonts/NotoSansSC.ttf',
    'FONT_MONO':  'C:/Windows/Fonts/consola.ttf',
    'FONT_SERIF': 'C:/Windows/Fonts/times.ttf',
}
_fcache = {}


def font(fam, size):
    key = (fam, size)
    if key not in _fcache:
        rel = FONTS.get(fam)
        p = os.path.join(FX, rel) if rel and not rel.startswith('C:') else rel
        try:
            _fcache[key] = ImageFont.truetype(p, int(size))
        except Exception:
            _fcache[key] = None
    return _fcache[key]


def text_w(text, size, ls, fam, scale_x=1.0):
    """CText/nowrap div 的墨迹宽：advance 求和 + letterSpacing*n，再乘 scaleX"""
    f = font(fam, size)
    if f is None:                       # 未知字体 → 启发式（与 layout_audit 同口径）
        cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
        adv = size * (cjk * 1.0 + (len(text) - cjk) * 0.60)
    else:
        adv = sum(f.getlength(ch) for ch in text)
    return (adv + ls * len(text)) * scale_x


# ---------------------------------------------------------------------------
# 图元量尺表：每个共用件「实际占用多大地方」+ 柔光外扩。
# 生产版应由「单图元渲染一次 + DOM 探针测量」自动生成（一次性、零图像 token）。
# ---------------------------------------------------------------------------
PARTS = {
    'HeroTLS': dict(kind='text', pad=34, note='墨迹 = 文本实测宽 ×150px；pad=柔光 34px',
                    box=lambda a: cent(n(a, 'cx', 620), n(a, 'cy', 300),
                                       text_w('TLS 1.3', 150, 3, 'FONT_WIDE'), 150)),
    'PaperCard': dict(kind='opaque', pad=0, note='实心黑底 Box',
                      box=lambda a: (n(a, 'x', 0), n(a, 'y', 0), n(a, 'w', 299), n(a, 'h', 340))),
    'MsgCard': dict(kind='opaque', pad=0, box=lambda a: (n(a, 'x'), n(a, 'y'), n(a, 'w'), n(a, 'h'))),
    'Envelope': dict(kind='opaque', pad=0, box=lambda a: (n(a, 'x'), n(a, 'y'), n(a, 'w'), n(a, 'h'))),
    'MiniPill': dict(kind='opaque', pad=0, box=lambda a: (n(a, 'x'), n(a, 'y'), n(a, 'w', 136), n(a, 'h', 44))),
    'PillCell': dict(kind='opaque', pad=0, box=lambda a: (n(a, 'x'), n(a, 'y'), n(a, 'w'), n(a, 'h'))),
    'TagBlock': dict(kind='opaque', pad=0, box=lambda a: (n(a, 'x'), n(a, 'y'), n(a, 'w', 237), n(a, 'h', 62))),
    'ClientBox': dict(kind='opaque', pad=0, box=lambda a: cent(n(a, 'cx'), n(a, 'cy'), n(a, 'h') * 1.3, n(a, 'h'))),
    'SubCN': dict(kind='text', pad=6, note='CJK 900 48px scaleX .8',
                  box=lambda a: cent(n(a, 'cx', 620), n(a, 'cy', 432),
                                     text_w(a.get('_text', ''), n(a, 'size', 48), 2, 'FONT_HEAVY', 0.8),
                                     n(a, 'size', 48) * 1.2)),
}
# deco：加光/描边轮廓，不遮挡，直接跳过
DECO = {'LightSweep', 'StageLine', 'GhostText', 'StarField', 'DotFieldBg', 'Fog', 'Vignette',
        'Grain', 'ProgressBar', 'Subtitle', 'Overlay', 'CameraRig', 'DashedTrail', 'ArrowH',
        'Svg', 'GlowRing', 'HaloRing', 'Sparkle', 'LightLeak', 'ScanLine', 'NoiseBg'}
# 可读文本类（可能被遮挡的一方）
TEXTY = {'CText', 'TechText', 'MonoText', 'Counter', 'BigNumber', 'HeroTLS', 'SubCN'}
ALL = set(PARTS) | DECO | TEXTY | {'Box', 'Pill'}


# ---------------------------------------------------------------------------
# 项目级量尺表 <项目根>/zorder_parts.json（可选）
# 审计器不可能硬编码认识每个项目的自定义图元；不在表里的共用件会落进「未解析」，
# 变成盲区，而盲区不会有任何报错 —— 所以覆盖率门禁把这件事顶到台面上。
# 结构：
#   {
#     "parts": { "PaperCard": {"kind":"opaque","pad":0,"note":"实心黑底",
#                              "box":{"type":"xywh","x":0,"y":0,"w":299,"h":340}} },
#     "deco":  ["MyGlowRing"],          // 追加「不遮挡」元件
#     "texty": ["MyBigYear"]            // 追加「可读文本」元件
#   }
#   box.type：xywh（用 x/y/w/h）· cent（用 cx/cy/w/h）· text（按文本实测宽，参数
#   text/size/ls/fam/scaleX，传 from_text:true 则用元素自身的文字内容）
# ---------------------------------------------------------------------------
REGPATH = 'zorder_parts.json'


def _box_from_spec(spec):
    """把 JSON 度量规格编译成 box(attrs) -> (x, y, w, h)"""
    t = spec.get('type', 'xywh')
    if t == 'xywh':
        return lambda a: (n(a, 'x', spec.get('x', 0)), n(a, 'y', spec.get('y', 0)),
                          n(a, 'w', spec.get('w', 0)), n(a, 'h', spec.get('h', 0)))
    if t == 'cent':
        return lambda a: cent(n(a, 'cx', spec.get('cx', 0)), n(a, 'cy', spec.get('cy', 0)),
                              n(a, 'w', spec.get('w', 0)), n(a, 'h', spec.get('h', 0)))
    if t == 'text':
        fixed = spec.get('text', '')
        use_own = bool(spec.get('from_text'))

        def _b(a):
            sz = n(a, 'size', spec.get('size', 32))
            return cent(n(a, 'cx', spec.get('cx', 0)), n(a, 'cy', spec.get('cy', 0)),
                        text_w((a.get('_text', '') if use_own else fixed) or fixed,
                               sz, n(a, 'letterSpacing', spec.get('ls', 0)),
                               spec.get('fam', 'FONT_HEAVY'),
                               n(a, 'scaleX', spec.get('scaleX', 1.0))),
                        sz * 1.2)
        return _b
    raise ValueError(f'未知 box.type: {t}')


def load_registry(project_root):
    """读 <项目根>/zorder_parts.json 与内置表合并（项目优先）。
    返回 (merged_parts, ok_names, problems)；problems 不静默吞。"""
    p = os.path.join(project_root, REGPATH)
    if not os.path.isfile(p):
        return dict(PARTS), [], []
    try:
        raw = json.load(open(p, encoding='utf-8'))
    except Exception as e:
        return dict(PARTS), [], [f'{REGPATH} 解析失败（本轮按内置表跑）：{e}']
    merged, ok, bad = dict(PARTS), [], []
    for name, spec in (raw.get('parts') or {}).items():
        try:
            merged[name] = dict(kind=spec.get('kind', 'opaque'),
                                pad=float(spec.get('pad', 0)),
                                note=spec.get('note', ''),
                                box=_box_from_spec(spec.get('box') or {}))
            ok.append(name)
        except Exception as e:
            bad.append(f'{name}: {e}')
    for name in (raw.get('deco') or []):
        DECO.add(name)
    for name in (raw.get('texty') or []):
        TEXTY.add(name)
    globals()['PARTS'] = merged
    globals()['ALL'] = set(merged) | DECO | TEXTY | {'Box', 'Pill'}
    return merged, ok, bad


def n(a, k, d=None):
    v = a.get(k, d)
    try:
        return float(v)
    except Exception:
        return float(d if d is not None else 0)


def cent(cx, cy, w, h):
    return (cx - w / 2, cy - h / 2, w, h)


# --------------------------- 源码解析 ---------------------------
RE_CONST = re.compile(r'^\s*const\s+([A-Za-z_]\w*)\s*=\s*([^;\n]+);', re.M)


def const_table(src):
    """把 const NAME = <数值表达式> 求出来（限定命名空间，不用 builtins）"""
    tbl = {}
    raw = {}
    for m in RE_CONST.finditer(src):
        raw[m.group(1)] = m.group(2).strip()
    fns = {'stagger': lambda i, step=2: i * step, 'clamp01': lambda v: v,
           'Math': type('M', (), {'round': round, 'abs': abs, 'min': min, 'max': max})}
    for _ in range(4):                       # 迭代解依赖
        for k, e in raw.items():
            if k in tbl:
                continue
            e2 = re.sub(r'\b([A-Za-z_]\w*)\b',
                        lambda mm: (repr(tbl[mm.group(1)]) if mm.group(1) in tbl else mm.group(1)), e)
            try:
                v = eval(e2, {'__builtins__': {}}, fns)     # noqa: S307  仅本地可信源码
                if isinstance(v, (int, float)):
                    tbl[k] = v
            except Exception:
                pass
    return tbl


def resolve(expr, tbl, default=None):
    expr = expr.strip().rstrip(',')
    expr = re.sub(r'^\{(.*)\}$', r'\1', expr).strip()
    if re.fullmatch(r'-?\d+(\.\d+)?', expr):
        return float(expr)
    try:
        v = eval(expr, {'__builtins__': {}},
                 {'stagger': lambda i, step=2: i * step, 'clamp01': lambda v: v,
                  'F0': tbl.get('F0'), **tbl})
        return float(v) if isinstance(v, (int, float)) else default
    except Exception:
        pass
    m = re.search(r'N\s*-\s*(\d{3,5})', expr)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r'N\s*>=\s*(\d{3,5})', expr)
    if m:
        return float(m.group(1))
    # 表达式里只有一个标识符时，回查 const 表
    for ident in re.findall(r'\b([A-Za-z_]\w*)\b', expr):
        if ident in tbl:
            return tbl[ident]
    return default


def attrs_of(tag_body):
    out = {}
    for m in re.finditer(r'\b([a-zA-Z]\w*)\s*=\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|"[^"]*"|\'[^\']*\'|[\w.]+)', tag_body):
        out[m.group(1)] = m.group(2).strip()
    return out


def lit(attrs, k, tbl):
    """取属性值：字面量 / const / 简单表达式"""
    if k not in attrs:
        return None
    v = attrs[k]
    if v.startswith(('"', "'")):
        return v[1:-1]
    v = v.strip('{}').strip()
    if re.fullmatch(r'-?\d+(\.\d+)?', v):
        return float(v)
    r = resolve(v, tbl)
    if r is not None:
        return r
    # `210 + cardDy` 这类「字面量 + 变量」：取前导字面量（动画偏移量通常远小于坐标）
    m = re.match(r'(-?\d+(?:\.\d+)?)', v)
    return float(m.group(1)) if m else None


def frame_in_expr(expr, ctbl):
    """从一个 const 定义表达式里抽出「激活帧」：N - 642 / N >= 666 / softOp(N-642,8) …"""
    out = []
    for m in re.finditer(r'N\s*[-<>=]+\s*([A-Za-z_]\w*|\d{2,5})', expr):
        tok = m.group(1)
        if tok.isdigit():
            out.append(float(tok))
        elif tok in ctbl:
            out.append(float(ctbl[tok]))
    return out


def build_enter_tables(src):
    """返回 (const 数值表, const→激活帧表)。"""
    ctbl = const_table(src)
    etbl = {}
    for m in RE_CONST.finditer(src):
        fr = frame_in_expr(m.group(2), ctbl)
        if fr:
            etbl[m.group(1)] = min(fr)
    return ctbl, etbl


RE_CAND = re.compile(r'(?:f0|opacity)\s*=\s*(\{[^{}]*\}|[\w.]+)')


def enter_of(slice_, back, ctbl, etbl):
    """元素入场帧。优先级（关键：避免被相邻元素污染）：
       1. 本元素**自身起始标签**里的 f0=
       2. 本元素自身标签里的 opacity= 所引用 const 的激活帧
       3. back 窗口里**最后一个** f0=（= 最靠近、包住它的那层 wrapper）
       4. 退化：切片里最早的字面帧 / F0
    """
    tag = slice_[:slice_.find('>') + 1] if '>' in slice_ else slice_

    m = re.search(r'f0\s*=\s*\{([^{}]*)\}', tag)
    if m:
        v = _f0_value(m.group(1), ctbl)
        if v is not None:
            return v

    best = None
    for m in RE_CAND.finditer(tag):
        f = _cand_value(m.group(1), ctbl, etbl)
        if f is not None and (best is None or f < best):
            best = f
    if best is not None:
        return float(best)

    ms = list(re.finditer(r'f0\s*=\s*\{([^{}]*)\}', back))
    if ms:
        v = _f0_value(ms[-1].group(1), ctbl)
        if v is not None:
            return v

    nums = [float(x) for x in re.findall(r'\b(\d{3,5})\b', slice_[:300])
            if 500 <= float(x) <= 3000]
    return float(min(nums)) if nums else float(ctbl.get('F0') or 0)


def _f0_value(expr, ctbl):
    e = expr.strip()
    mm = re.fullmatch(r'([A-Za-z_]\w*)\s*\+\s*stagger\((\d+)[^)]*\)', e)
    if mm and mm.group(1) in ctbl:
        return float(ctbl[mm.group(1)]) + 2 * int(mm.group(2))
    v = resolve(e, ctbl)
    return float(v) if v is not None and 100 <= float(v) <= 3000 else None


def _cand_value(c, ctbl, etbl):
    c = c.strip().strip('{}').strip()
    f = None
    if re.fullmatch(r'\d{1,5}(\.\d+)?', c):
        f = float(c)
    elif c in etbl:
        f = float(etbl[c])
    elif c in ctbl:
        f = float(ctbl[c])
    else:
        v = resolve(c, ctbl)
        f = float(v) if v is not None else None
    return f if f is not None and 100 <= f <= 3000 else None


def scan_items(src, ctbl, etbl):
    """按源码顺序抽出顶层可绘制元素（近似：取标签起点到下一个可绘制标签起点之间的切片）"""
    starts = []
    for m in re.finditer(r'<([A-Z][A-Za-z0-9]*)\b', src):
        if m.group(1) in ALL:
            starts.append((m.start(), m.group(1)))
    items = []
    for i, (pos, comp) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(src)
        slice_ = src[pos:end]
        # 往回看 260 字符，捕捉外层包着的 `{N >= T_X ? (` 与 `<SoftIn f0={...}>`
        back = src[max(0, pos - 260):pos]
        attrs = attrs_of(slice_[:slice_.find('>') + 1]) if '>' in slice_ else {}
        ent = enter_of(slice_, back, ctbl, etbl)
        # 文本内容（给 SubCN / CText 这类需要文字的件用）
        tm = re.search(RE_TEXT_CHILD, slice_, re.S)
        txt = tm.group(1).strip() if tm else ''
        if not txt:
            m2 = re.search(RE_TEXT_IDENT, slice_, re.S)
            if m2:
                nm = m2.group(1)
                # `{year}` 这类取不到字面值：数字型标识符按 4 位数字估宽，其余用标识符本身
                txt = '0000' if re.search(r'(year|num|cnt|count|val|pct|idx|n)$', nm, re.I) else nm
        items.append(dict(comp=comp, pos=pos, enter=float(ent), slice=slice_, attrs=attrs,
                          text=txt, back=back))
    return items


def rslice_text_after(slice_):
    return r'>\s*\n?\s*([^<>{}]{1,40}?)\s*\n?\s*<'


RE_TEXT_CHILD = r'>\s*\n?\s*([^<>{}]{1,40}?)\s*\n?\s*<'
RE_TEXT_IDENT = r'>\s*\n?\s*\{([A-Za-z_][\w.]*)\}\s*\n?\s*<'


def wrapper_offset(back, tbl):
    """从「最近的一层 wrapper」里取 left/top 偏移；取不到返回 None（宁可漏，不要错）"""
    ml = mt = None
    for m in re.finditer(r'left:\s*(-?[\d.]+)', back):
        ml = float(m.group(1))
    for m in re.finditer(r'top:\s*(-?[\d.]+)', back):
        mt = float(m.group(1))
    if ml is None and mt is None:
        return None
    return (ml or 0.0, mt or 0.0)


def rect_of(it, tbl):
    comp, a, slice_ = it['comp'], it['attrs'], it['slice_'] if 'slice_' in it else it['slice']
    if comp in PARTS:
        spec = PARTS[comp]
        aa = {'_text': it['text'], '_back': it.get('back', '')}
        # 只收「确实解析成数字」的属性；解析失败的一律不放进 aa，交给量尺表默认值
        for k in ('x', 'y', 'w', 'h', 'cx', 'cy', 'size'):
            v = lit(a, k, tbl)
            if isinstance(v, (int, float)):
                aa[k] = v
        r = spec['box'](aa)
        # wrapper 局部坐标：`<div style={{left:910, top:cardY}}><PaperCard x={0} y={0}/>`
        # 这是 layout_audit.py 时代已证实的静态不可解来源之一；这里做「左/上偏移可解析才修」的保守处理
        if abs(r[0]) < 1.5 and abs(r[1]) < 1.5:
            off = wrapper_offset(aa.get('_back', ''), tbl)
            if off is not None:
                r = (r[0] + off[0], r[1] + off[1], r[2], r[3])
        return r, spec.get('pad', 0), 'part'
    if comp in ('CText', 'TechText', 'Counter', 'BigNumber', 'MonoText'):
        cx, cy = lit(a, 'cx', tbl), lit(a, 'cy', tbl)
        size = lit(a, 'size', tbl) or lit(a, 'fontSize', tbl) or 32
        ls = lit(a, 'letterSpacing', tbl) or 0
        sx = lit(a, 'scaleX', tbl) or 1
        if cx is None or cy is None:
            return None, 0, 'unresolved'          # cx={HERO.cx} 这类不可静态求值
        fam = 'FONT_HEAVY'
        for f in FONTS:
            if f in str(a.get('family', '')):
                fam = f
        w = text_w(it['text'], size, ls, fam, sx)
        pad = 6
        m = re.search(r'0\s+0\s+(\d+)px', slice_)
        if m:
            pad = max(pad, float(m.group(1)))
        # 局部坐标 (0,0)：由外层 wrapper 定位（layout_audit 时代已证实的静态盲区）
        if abs(cx) < 1.5 and abs(cy) < 1.5:
            off = wrapper_offset(it.get('back', ''), tbl)
            if off is None or 'translate(-50%' not in it.get('back', ''):
                return None, 0, 'unresolved'
            return (off[0] - w / 2, off[1] - size * 1.2 / 2, w, size * 1.2), pad, 'text'
        return cent(cx, cy, w, size), pad, 'text'
    if comp == 'Box' or comp == 'Pill':
        x, y, w, h = (lit(a, k, tbl) for k in ('x', 'y', 'w', 'h'))
        if None in (x, y, w, h):
            return None, 0, 'unresolved'
        return (x, y, w, h), 0, 'box'
    return None, 0, 'unresolved'


def inter(r1, r2):
    x0 = max(r1[0], r2[0]); x1 = min(r1[0] + r1[2], r2[0] + r2[2])
    y0 = max(r1[1], r2[1]); y1 = min(r1[1] + r1[3], r2[1] + r2[3])
    return max(0.0, x1 - x0), max(0.0, y1 - y0)


def audit_file(path):
    src = open(path, encoding='utf-8').read()
    ctbl, etbl = build_enter_tables(src)
    items = scan_items(src, ctbl, etbl)
    drawn = []
    unresolved = []
    deco_n = 0
    for it in items:
        if it['comp'] in DECO:                # 加光/轮廓/容器：不遮挡，静默跳过
            deco_n += 1
            continue
        r, pad, how = rect_of(it, ctbl)
        if r is None:
            unresolved.append(it['comp'])
            continue
        if r[2] < 20 or r[3] < 16:            # 退化矩形（坐标没解析出来）→ 不计入，避免假阳性
            unresolved.append(it['comp'])
            continue
        drawn.append(dict(comp=it['comp'], rect=r, pad=pad, enter=it['enter'],
                          how=how, text=it['text'],
                          op=(it['attrs'].get('opacity') or '')))
    findings = []
    for i in range(len(drawn)):
        for j in range(i + 1, len(drawn)):
            B, A = drawn[i], drawn[j]          # A 在 DOM 里更靠后 → 画在 B 之上
            # 全屏分组容器不参与
            if A['rect'][2] >= 1100 and A['rect'][3] >= 560:
                continue
            if B['rect'][2] >= 1100 and B['rect'][3] >= 560:
                continue
            ra = (A['rect'][0] - A['pad'], A['rect'][1] - A['pad'], A['rect'][2] + 2 * A['pad'], A['rect'][3] + 2 * A['pad'])
            rb = (B['rect'][0] - B['pad'], B['rect'][1] - B['pad'], B['rect'][2] + 2 * B['pad'], B['rect'][3] + 2 * B['pad'])
            ow, oh = inter(ra, rb)
            if ow < 4 or oh < 4:
                continue
            area = ow * oh
            if area < 1200:
                continue
            # 墨迹盒（不含柔光外扩）的重叠 —— 用来分级
            owi, ohi = inter(A['rect'], B['rect'])
            areai = owi * ohi
            sev = '高' if areai >= 1200 else '中'
            note = '' if sev == '高' else '仅柔光/外扩区相交，墨迹本身未重叠'
            ov = [round(ow, 1), round(oh, 1), round(area)]
            ov_i = [round(owi, 1), round(ohi, 1), round(areai)]
            # Z1 层序倒置：B 后入场却被 A 压住
            if B['enter'] > A['enter'] + 2 and B['enter'] - A['enter'] <= 200:
                findings.append(dict(rule='Z1', sev=sev, note=note,
                                     what=f"{B['comp']}(入场{int(B['enter'])}) 被更早入场的 {A['comp']}(入场{int(A['enter'])}) 压在下面",
                                     overlap=ov, overlap_ink=ov_i,
                                     B=B['comp'], A=A['comp'], t=int(B['enter']),
                                     how=f"{B['how']}/{A['how']}"))
            # Z2 同帧叠字
            elif abs(B['enter'] - A['enter']) <= 6 and B['comp'] in TEXTY and A['comp'] in TEXTY:
                rbb = max(B['rect'][2] * B['rect'][3], 1)
                if area / rbb > 0.15:
                    findings.append(dict(rule='Z2', sev='中', note='同帧入场',
                                         what=f"{A['comp']} 与 {B['comp']} 同帧入场且墨迹相交",
                                         overlap=ov, overlap_ink=ov_i,
                                         B=B['comp'], A=A['comp'], t=int(A['enter']),
                                         how=f"{B['how']}/{A['how']}"))
    return dict(file=os.path.basename(path), n_items=len(drawn), unresolved=unresolved,
                deco_n=deco_n, findings=findings,
                items=[dict(comp=d['comp'], rect=[round(v, 1) for v in d['rect']],
                            pad=d['pad'], enter=int(d['enter']), how=d['how'], text=d['text'])
                       for d in drawn])


def find_project_root(p):
    """从 shots 目录往上找含 public/fonts 的项目根（字体度量要用真实字体文件）"""
    cur = os.path.abspath(p)
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, 'public', 'fonts')):
            return cur
        nxt = os.path.dirname(cur)
        if nxt == cur:
            break
        cur = nxt
    return os.path.abspath(p)


def main():
    global FX
    if len(sys.argv) < 2:
        print(__doc__); return 1
    argv = sys.argv[1:]
    root = argv[0]

    def opt(name, default=None, cast=str):
        if name in argv and argv.index(name) + 1 < len(argv):
            try:
                return cast(argv[argv.index(name) + 1])
            except Exception:
                return default
        return default

    FX = find_project_root(root)
    jout = opt('--json')
    mout = opt('--md')
    gate = '--gate' in argv
    max_high = opt('--max-high', 0, int)
    min_cov = opt('--min-coverage', 90.0, float)
    _parts, reg_ok, reg_bad = load_registry(FX)
    shots = []
    for g in sorted(os.listdir(root)):
        gd = os.path.join(root, g)
        if not os.path.isdir(gd):
            continue
        for f in sorted(os.listdir(gd)):
            if re.match(r'SC\d+\.tsx$', f):
                shots.append((g, os.path.join(gd, f)))
    if not shots:                      # 根目录直接放 SC*.tsx（如 _runs/C0_G2）
        for f in sorted(os.listdir(root)):
            if re.match(r'SC\d+\.tsx$', f):
                shots.append((os.path.basename(root), os.path.join(root, f)))
    L = []
    L.append('=' * 84)
    L.append(f'层序/空间占用审计 · {len(shots)} 个镜头 · 零图像 token')
    L.append('=' * 84)
    tot = 0
    hi = 0
    res = {}
    for g, p in shots:
        r = audit_file(p)
        res[f'{g}/{r["file"]}'] = r
        tot += len(r['findings'])
        hi += sum(1 for f in r['findings'] if f['sev'] == '高')
        flag = '⚠' if r['findings'] else '✓'
        un = f'  ⚠未解析 {len(r["unresolved"])}：{",".join(sorted(set(r["unresolved"])))}' if r['unresolved'] else ''
        L.append(f'{flag} {g}/{r["file"]:<12} 可审对象 {r["n_items"]:>2}  命中 {len(r["findings"])}'
                 f'  跳过加光 {r["deco_n"]}{un}')
        for f in r['findings']:
            L.append(f'      [{f["sev"]}·{f["rule"]}] {f["what"]}')
            L.append(f'           外扩区重叠 {f["overlap"][0]}×{f["overlap"][1]}px = {f["overlap"][2]}px²'
                     f'  |  墨迹重叠 {f["overlap_ink"][0]}×{f["overlap_ink"][1]}px = {f["overlap_ink"][2]}px²'
                     f'  @帧{f["t"]}  {f["how"]}')
            if f.get('note'):
                L.append(f'           注：{f["note"]}')
    ti = sum(r['n_items'] for r in res.values())
    tu = sum(len(r['unresolved']) for r in res.values())
    cov = 100 * ti / max(ti + tu, 1)
    L.append('=' * 84)
    L.append(f'合计命中 {tot} 条（高 {hi} / 中 {tot - hi}）')
    L.append(f'可审覆盖率：已解析 {ti} / 内容对象 {ti + tu} = {cov:.1f}%（未解析的即审计盲区）')
    L.append(f'跳过加光/轮廓元素 {sum(r["deco_n"] for r in res.values())} 个（按设计不参与遮挡判定）')
    if reg_ok:
        L.append(f'项目量尺表：已并入 {len(reg_ok)} 个件（{",".join(reg_ok[:12])}'
                 f'{"…" if len(reg_ok) > 12 else ""}）')
    for b in reg_bad:
        L.append(f'⚠ 项目量尺表问题：{b}')
    if tu:
        L.append('')
        L.append('未解析清单（审计盲区 → 每个都要么补进 ' + REGPATH + '，要么按 §13 改成字面量坐标）：')
        for k in sorted(res):
            un = sorted(set(res[k]['unresolved']))
            if un:
                L.append(f'  {k}：{",".join(un)}')
    verdict_lines = []
    if hi > max_high:
        verdict_lines.append(f'层序高严重度 {hi} 条 > 上限 {max_high}')
    if cov < min_cov:
        verdict_lines.append(f'可审覆盖率 {cov:.1f}% < 下限 {min_cov:.1f}%')
    ok = not verdict_lines
    if gate:
        L.append('=' * 84)
        L.append(('门禁通过 ✓' if ok else '门禁不通过 ✗') +
                 ('' if ok else '：' + '；'.join(verdict_lines)))
    txt = '\n'.join(L)
    if jout:
        json.dump({'shots': res, 'totals': dict(hits=tot, high=hi, mid=tot - hi,
                                                resolved=ti, unresolved=tu,
                                                coverage_pct=round(cov, 1),
                                                gate=gate, gate_pass=ok if gate else None,
                                                gate_reasons=verdict_lines,
                                                registry=list(reg_ok)),
                   }, open(jout, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if mout:
        open(mout, 'w', encoding='utf-8').write(txt)
    print(txt)
    return 1 if (gate and not ok) else 0


if __name__ == '__main__':
    sys.exit(main())
