#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gen_api_index.py —— 从 ui.tsx / fx.tsx 生成「图元 API 签名索引」。

用途：C2/C3/C4 档用本索引替代 `ui.tsx` 全文（10,916 tok → ≈1.5K tok）。
索引只保留**调用所需信息**：组件名、props 名、默认值、以及色/光/帧工具常量；
实现细节、样式推导、注释一律丢弃。

用法：
  python gen_api_index.py <项目根>                  # 读 <项目根>/src/{ui,fx}.tsx，打印
  python gen_api_index.py <项目根> --out <路径>      # 写文件
  python gen_api_index.py <项目根> --budget 1500    # 超预算则非零退出（供 CI/自检）
"""
import os
import re
import sys
import argparse


def toks_text(s):
    cjk = len(re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', s))
    return int(cjk * 0.7 + (len(s) - cjk) * 0.28)


def slice_paired(s, i, op, cl):
    """s[i] == op，返回 (配对内容, 闭合后索引)；支持嵌套。找不到闭合则返回余下全文。"""
    depth, j = 0, i
    while j < len(s):
        if s[j] == op:
            depth += 1
        elif s[j] == cl:
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def parse_props(type_str):
    """把 'cx: number; cy: number; weight?: number' 拆成 [(name, optional), ...]"""
    out = []
    for part in type_str.split(';'):
        part = part.strip()
        if not part:
            continue
        m = re.match(r'^(\w+)(\?)?\s*:', part)
        if m:
            out.append((m.group(1), bool(m.group(2))))
    return out


def parse_defaults(destr):
    """把 '{cx, cy, weight = 700, dy = TEXT_DY}' 拆成 {name: default|None}（自动剥外层大括号）"""
    destr = destr.strip()
    if destr.startswith('{') and destr.endswith('}'):
        destr = destr[1:-1]
    out = {}
    depth = 0
    cur = ''
    parts = []
    quote = None            # 引号内的逗号不分割（如模板串里的 `…, 0 0 28px rgba(…)`）
    for ch in destr:
        if quote:
            if ch == quote:
                quote = None
            cur += ch
            continue
        if ch in '"\'`':
            quote = ch
            cur += ch
            continue
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if '=' in p:
            k, v = p.split('=', 1)
            out[k.strip()] = ' '.join(v.split())
        else:
            out[p] = None
    return out


def shorten(v):
    """默认值压缩：去掉类型断言与内部空格"""
    if v is None:
        return None
    v = re.sub(r'\s+', ' ', v.strip())
    # 常见长字面量：URL / 长 shadow 串削成可读短形
    if len(v) > 46 and (v.startswith("'") or v.startswith('`')):
        return "…"
    return v


def collect_types(src):
    """收集 export type X = {...} 与 export type X = Y & {...}
    （必须按配对解析：类型体内含分号，用 [^;]+ 会在第一个 prop 处截断）"""
    types = {}
    for m in re.finditer(r'export type (\w+)\s*=\s*', src):
        name, i = m.group(1), m.end()
        depth, j = 0, i
        while j < len(src):
            ch = src[j]
            if ch in '{[(':
                depth += 1
            elif ch in '}])':
                depth -= 1
            elif ch == ';' and depth <= 0:
                break
            j += 1
        types[name] = src[i:j]
    # 展开一层继承（PillProps = BoxProps & {...}）
    for _ in range(3):
        changed = False
        for k, v in list(types.items()):
            m = re.match(r'^(\w+)\s*&\s*(\{.*\})$', v.strip(), re.S)
            if m and m.group(1) in types:
                types[k] = types[m.group(1)].strip().rstrip(';') + '; ' + m.group(2)
                changed = True
        if not changed:
            break
    return types


def collect_const_groups(src):
    """色 / 光 / 几何常量：export const NAME = '字面量'"""
    colors, glows, others = [], [], []
    for m in re.finditer(r"export const (\w+)\s*=\s*'([^']*)'\s*;", src):
        name, val = m.group(1), m.group(2)
        if re.match(r'^#|^rgb', val):
            colors.append((name, val))
        elif re.search(r'\d+px', val):
            glows.append((name, val))
        else:
            others.append((name, val))
    return colors, glows, others


def fmt_glow(val):
    """'0 0 12px 3px rgba(102,45,248,.35), 0 0 42px 14px rgba(...)' → '12px/3px + 42px/14px'"""
    parts = []
    for seg in val.split(','):
        nums = re.findall(r'(\d+px)(?:\s+(\d+px))?', seg)
        for a, b in nums:
            parts.append(a + ('/' + b if b else ''))
    return '+'.join(parts) if parts else val[:40]


def gen(ui_src, fx_src, title):
    lines = []
    for fname, src, tag in ((None, ui_src, 'ui'), (None, fx_src, 'fx')):
        if src is None:
            continue
        types = collect_types(src)
        colors, glows, others = collect_const_groups(src)

        lines.append('## %s.tsx  (import {…} from \'../../%s\')' % (tag, tag))

        if colors:
            lines.append('- 色: ' + ' · '.join('%s %s' % (n, v) for n, v in colors))
        if glows:
            seg = ' · '.join('%s(%s)' % (n, fmt_glow(v)) for n, v in glows)
            lines.append('- 光: ' + seg)
            lines.append('  ⚠ 含 spread（4 长度）→ **只能当 boxShadow**；当 textShadow 会被整条丢弃')
        if others:
            lines.append('- 常量: ' + ' · '.join('%s=%s' % (n, v) for n, v in others))

        # 组件（用配对扫描：泛型与解构里都可能有嵌套括号 / 尖括号）
        comps, fns = [], []
        for m in re.finditer(r'export const (\w+)\s*:\s*React\.FC\s*<', src):
            name = m.group(1)
            gtype, p = slice_paired(src, m.end() - 1, '<', '>')
            gtype = gtype.strip()
            q = src.find('(', p)
            if q < 0:
                continue
            destr, _ = slice_paired(src, q, '(', ')')
            if gtype.startswith('{'):
                inner = gtype
            elif gtype in types:
                inner = types[gtype]
            else:
                inner = ''
            inner = re.sub(r'[{}\[\]]', '', inner)   # 剥掉所有括号，避免段首 prop 被吞
            props = parse_props(inner)
            default_map = parse_defaults(destr)
            if not props:
                comps.append(name)
                continue
            toks = [name]
            for pname, _opt in props:
                # children / style 每个组件都有，统一在文件头说明，不逐条占 token
                if pname in ('children', 'style'):
                    continue
                dv = shorten(default_map.get(pname))
                toks.append('%s=%s' % (pname, dv) if dv is not None else pname)
            comps.append(' '.join(toks))

        # 函数
        for m in re.finditer(r'export const (\w+)\s*=\s*\(([^)]*)\)\s*(?::[^=]+)?=>', src):
            name, args = m.group(1), m.group(2)
            out_args = []
            for a in args.split(','):
                a = a.strip()
                if not a:
                    continue
                if '=' in a:                       # 有默认值：name = default（丢类型注解）
                    k, v = a.split('=', 1)
                    out_args.append('%s=%s' % (k.split(':')[0].strip(), v.strip()))
                else:                              # 无默认值：name?（可选）或 name（必填）
                    head = a.split(':')[0].strip()
                    out_args.append(head if head.endswith('?') else head)
            fns.append('%s(%s)' % (name, ', '.join(out_args)))

        seen = set()
        if fns:
            lines.append('- 函数: ' + ' · '.join(f for f in fns if not (f in seen or seen.add(f))))
        lines.append('- 组件（props 无默认值者必填）:')
        for c in comps:
            lines.append('  ' + c)
        lines.append('')
    head = '# 图元 API 索引（自动生成，勿手改）\n\n' \
           '> 由 `scripts/gen_api_index.py` 从 `src/ui.tsx` / `src/fx.tsx` 提取签名。\n' \
           '> 实现细节与样式推导请直接看源码对应行，不要凭索引猜。\n' \
           '> 所有组件都接受 `style?: React.CSSProperties` 与 `children`（已略）；`props 无默认值者必填`。\n\n'
    return head + '\n'.join(lines).rstrip() + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--out', default=None)
    ap.add_argument('--budget', type=int, default=0)
    a = ap.parse_args()

    p_ui = os.path.join(a.root, 'src', 'ui.tsx')
    p_fx = os.path.join(a.root, 'src', 'fx.tsx')
    ui = open(p_ui, encoding='utf-8').read() if os.path.exists(p_ui) else None
    fx = open(p_fx, encoding='utf-8').read() if os.path.exists(p_fx) else None
    if ui is None and fx is None:
        print('找不到 %s / %s' % (p_ui, p_fx))
        return 2

    out = gen(ui, fx, a.root)
    t = toks_text(out)
    if a.out:
        open(a.out, 'w', encoding='utf-8').write(out)
        print('已写入 %s  %d 字符  ≈%d tokens' % (a.out, len(out), t))
    else:
        print(out)
    for p in (p_ui, p_fx):
        if p and os.path.exists(p):
            print('  源 %s %d tokens' % (os.path.basename(p), toks_text(open(p, encoding='utf-8').read())))
    if a.budget and t > a.budget:
        print('⚠ 超预算：%d > %d' % (t, a.budget))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
