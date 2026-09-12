#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
slice.py —— 把项目侧的三个大文件切成「本构建组专用」的小切片。

C0：每次派单读 `分镜表.md`(8.2K) + `timeline.md`(1.6K) + `research/调研.md`(12.2K) ≈ 22,000 tok。
C2：只读本组切片，≈4,500 tok。切片里的每一条都能在原文里找到，**不新增任何内容**。

产出（默认写回项目内约定位置）：
  <项目根>/script/storyboard_Gn.md   本组分镜（镜头表 + 与本组相关的全局约束）
  <项目根>/script/timeline_Gn.md     本组帧区间覆盖的句（含字数与块文本）
  <项目根>/research/facts_Gn.md      本组画面允许出现的数字/术语 + 其调研出处行

用法：
  python slice.py <项目根> --group G2
  python slice.py <项目根> --group G2 --budget-storyboard 1500 --budget-facts 1500
"""
import os
import re
import sys
import argparse


def toks_text(s):
    cjk = len(re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', s))
    return int(cjk * 0.7 + (len(s) - cjk) * 0.28)


def read(p):
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ''


# ---------------- 分镜表 ----------------
def split_storyboard(text):
    """→ (共 4 个键：groups{id: (title, header, rows[], start_line)}, global_lines[])"""
    lines = text.splitlines()
    groups, global_lines = {}, []
    cur = None
    in_global = False
    for i, l in enumerate(lines):
        m = re.match(r'^##\s+(G\d+)\s*(.*)$', l.strip())
        if m:
            cur = m.group(1)
            groups[cur] = {'title': l.strip(), 'header': '', 'rows': [], 'line': i + 1}
            in_global = False
            continue
        if re.match(r'^##\s+全局约束', l.strip()):
            in_global = True
            cur = None
            continue
        if re.match(r'^##\s+', l.strip()):
            cur, in_global = None, False
            continue
        if in_global:
            global_lines.append(l)
            continue
        if cur:
            s = l.strip()
            if s.startswith('|'):
                if re.match(r'^\|[\s:|-]+\|$', s):
                    continue
                if re.match(r'^\|\s*镜头\s*\|', s):            # 表头只认第一列是「镜头」
                    groups[cur]['header'] = s
                elif s.startswith('| SC'):
                    groups[cur]['rows'].append(s)
    return groups, global_lines


def pick_global(global_lines, ids, chapter):
    """从全局约束里裁出与本组相关的条目"""
    head, hl, cam, rest = [], [], [], []
    mode = None
    for l in global_lines:
        s = l.strip()
        if re.match(r'^\d+\.', s):
            if '高光时刻清单' in s:
                mode = 'hl'          # 标题由 build_storyboard 带内容时输出，此处不留空标题
                continue
            if '运镜清单' in s:
                mode = 'cam'
                continue
            if '§9 持续动作' in s:
                head.append('7. **§9 持续动作** → 见构建契约 §6（C0 全文见 composition-and-light.md §7）。')
                mode = 'skip9'
                continue
            mode = None
            if '复用图元' in s:      # 与 api-index 重复，换成指针
                head.append('3. 复用图元与调色板清单见 `reference/api-index.md`（本片全部组件/常量/函数签名）。')
                continue
            # 事实清单第 1 条很长：只留「不得出现」的禁用项，允许项交给 facts_Gn.md
            if re.match(r'^1\.', s):
                ban = re.search(r'\*\*不得在画面上出现(.*)$', s)
                head.append('1. 画面数字/术语的允许清单见 `research/facts_G%d.md`；%s'
                            % (chapter, ('**不得出现' + ban.group(1)) if ban else '不得自创。'))
                continue
            head.append(s)
            continue
        if mode == 'skip9':
            continue
        if mode and s.startswith('-'):
            if mode == 'hl':
                if any((' ' + i) in s or s.startswith('- ' + i) for i in ids):
                    hl.append(s)
            elif mode == 'cam':
                if re.search(r'第 %d 章' % chapter, s) or any((' ' + i) in s for i in ids):
                    cam.append(s)
            continue
        if mode:
            # 清单后的说明行
            (hl if mode == 'hl' else cam).append(s)
            continue
        if s:
            rest.append(s)
    return head, hl, cam, rest


def build_storyboard(root, group, groups, global_lines):
    g = groups.get(group)
    if not g:
        return None, []
    ids = []
    for r in g['rows']:
        m = re.match(r'^\|\s*(SC\d+)', r)
        if m:
            ids.append(m.group(1))
    ch = 1
    m = re.search(r'第\s*(\d+)\s*章', g['title'])
    if m:
        ch = int(m.group(1))
    head, hl, cam, rest = pick_global(global_lines, ids, ch)

    out = ['# %s 构建切片（%s）' % (group, g['title'].lstrip('# ').strip()),
           '',
           '> 由 `scripts/slice.py` 从 `分镜表.md` 切出，**未新增任何内容**；帧区间以本文件为准。',
           '> 坐标是参考值，可在保证安全区与风格的前提下微调。通用规则见构建契约。',
           '> 本组镜头：%s' % ' · '.join(ids),
           '']
    out.append('## 本组镜头表')
    out.append(g['header'] or '| 镜头 | 帧 | 节拍（字幕块起始） | 画面 | 动效 | 主角·尺寸 | 光 |')
    out.append('|---|---|---|---|---|---|---|')
    out += g['rows']
    out.append('')
    out.append('## 全局约束（已裁到本组）')
    out += head
    if hl:
        out.append('5. **高光时刻清单（本组）**：')
        out += hl
    if cam:
        out.append('6. **运镜清单（本章）**：')
        out += cam
    if rest:
        out += rest
    out.append('')
    return '\n'.join(out) + '\n', ids


# ---------------- 时间轴 ----------------
def build_timeline(root, group, ids, groups):
    tl = read(os.path.join(root, 'script', 'timeline.md'))
    if not tl:
        return None
    # 本组帧区间
    lo, hi = None, None
    for r in groups[group]['rows']:
        cells = [c.strip() for c in r.strip().strip('|').split('|')]
        if len(cells) > 1:
            m = re.match(r'^(\d+)\s*[–\-]\s*(\d+)$', cells[1])
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                lo = a if lo is None else min(lo, a)
                hi = b if hi is None else max(hi, b)
    keep, header = [], ''
    for l in tl.splitlines():
        s = l.strip()
        if s.startswith('| 句'):
            header = s
            continue
        if s.startswith('|') and re.match(r'^\|[\s:|-]+\|$', s):
            continue
        if s.startswith('| S'):
            cells = [c.strip() for c in s.strip('|').split('|')]
            m = re.match(r'^(\d+)\s*[–\-]\s*(\d+)$', cells[2]) if len(cells) > 2 else None
            if m and lo is not None and not (int(m.group(2)) < lo or int(m.group(1)) > hi):
                keep.append(s)
    out = ['# 本组时间轴切片（%s，帧 %d–%d）' % (group, lo or 0, hi or 0), '',
           '> 从 `script/timeline.md` 切出。字幕由共用层自动渲染，**镜头里不要再画字幕**。',
           '> 块起始帧见分镜表「节拍」列。', '']
    if header:
        out += [header, '|---|---|---|---|---|']
    out += keep
    return '\n'.join(out) + '\n'


# ---------------- 事实切片 ----------------
NUM = re.compile(r'\d+(?:\.\d+)?\s*%?|\b(?:RFC|TLS|IETF|OTP|RTT|X25519|secp\w+|HelloRetryRequest|Cloudflare|session\s+ticket|key\s+share|ClientHello)\b')
TICK = re.compile(r'`([^`]{2,32})`')


def load_api_names(root=None):
    """从 api-index.md 读组件/常量/函数名，用于把 API 名从「事实 token」里剔除。
    多路径回退：环境变量 A2E_SKILL → 自身位置推导（template/scripts → skill 根）→ 项目根。
    找不到就返回空集（仅少一层过滤，不影响可用性）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    cands = []
    if os.environ.get('A2E_SKILL'):
        cands.append(os.path.join(os.environ['A2E_SKILL'], 'reference', 'api-index.md'))
    cands.append(os.path.join(os.path.dirname(os.path.dirname(here)), 'reference', 'api-index.md'))
    cands.append(os.path.expanduser(os.path.join('~', '.workbuddy', 'skills',
                                                'anything2explainer', 'reference', 'api-index.md')))
    if root:
        cands.append(os.path.join(root, 'reference', 'api-index.md'))
    t = ''
    for p in cands:
        t = read(p)
        if t:
            break
    names = set()
    for m in re.finditer(r'^  (\w+)', t, re.M):           # 组件行（缩进两空格）
        names.add(m.group(1))
    for sec in re.finditer(r'^- (?:色|光|常量|函数):(.*)$', t, re.M):
        for m in re.finditer(r'(\w+)\s*[\s(·]', sec.group(1)):
            names.add(m.group(1))
    return names


def is_noise(t, names):
    if t in names:
        return True
    if re.search(r'px|deg|rgba|scaleX|pow|Pow|clamp|ease', t):
        return True
    return False


def facts_tokens(rows, names):
    """从本组分镜行的「画面/动效/主角/光」列抽事实 token（剔除坐标、尺寸、API 名）"""
    toks = {}
    for r in rows:
        cells = [c.strip() for c in r.strip().strip('|').split('|')]
        body = ' '.join(cells[3:])          # 跳过 镜头/帧/节拍
        body = re.sub(r'[（(]\s*\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\s*[)）]', ' ', body)  # 坐标 (x,y)
        body = re.sub(r'\d+(?:\.\d+)?\s*(?:px|×|x)\s*\d*', ' ', body)                 # 尺寸 Npx / N×M
        body = re.sub(r'\d+(?:\.\d+)?\s*→\s*\d+(?:\.\d+)?', ' ', body)                # 轴范围 a→b
        for m in TICK.finditer(body):
            v = m.group(1).strip()
            if re.search(r'[A-Za-z]', v) and not is_noise(v, names):
                toks.setdefault(v, True)
        for m in NUM.finditer(body):
            v = m.group(0).strip()
            # 只留「含字母 / 带百分号 / 版本号」的：剩下的是裸数字（行号、序号、坐标），
            # 一律是噪声，留在里面会把真命中冲淡。权威清单看文末 §7。
            if re.search(r'[A-Za-z]', v) or '%' in v or re.match(r'^\d+\.\d+$', v):
                if not is_noise(v, names):
                    toks.setdefault(v, True)
    return list(toks)


def build_facts(root, group, rows):
    res = read(os.path.join(root, 'research', '调研.md'))
    names = load_api_names(root)
    toks = facts_tokens(rows, names)
    rl = res.splitlines()
    hits = []
    for t in sorted(toks, key=lambda x: (not bool(re.search(r'[A-Za-z]', x)), -len(x))):
        found = [str(i + 1) for i, l in enumerate(rl) if t in l]
        if found:                      # 只输出有出处的：未命中多半是坐标/尺寸，不占篇幅
            hits.append((t, found[:4]))
    out = ['# 事实切片（%s）' % group, '',
           '> 由 `scripts/slice.py` 从 `research/调研.md` 抽行。规则：**画面上出现的数字/术语必须能在此找到依据**，',
           '> 本文件之外的一律不写。文末两份清单为原文照抄（未加工），是权威依据。', '',
           '## 本组画面 token → 调研出处行']
    for t, ls in hits:
        out.append('- `%s` → L%s' % (t, '、L'.join(ls)))
    for tag, pat in (('§7 数字与比喻清单', r'^##\s*§7'), ('§8 术语中英对照', r'^##\s*§8')):
        sec, on = [], False
        for l in rl:
            if re.match(pat, l.strip()):
                on = True
                sec.append(l)
                continue
            if on and re.match(r'^##\s+', l.strip()):   # 只被同级标题截断（节内有 ### 子标题）
                break
            if on:
                sec.append(l)
        if sec:
            out += ['', '## 调研 %s（原文照抄）' % tag, ''] + sec
    return '\n'.join(out) + '\n', toks, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--group', required=True)
    ap.add_argument('--budget-storyboard', type=int, default=0)
    ap.add_argument('--budget-facts', type=int, default=0)
    ap.add_argument('--dry', action='store_true', help='只量不写')
    a = ap.parse_args()

    sb_text = read(os.path.join(a.root, '分镜表.md'))
    if not sb_text:
        print('找不到 %s/分镜表.md' % a.root)
        return 2
    groups, gl = split_storyboard(sb_text)
    if a.group not in groups:
        print('分镜表里没有 %s（现有：%s）' % (a.group, ', '.join(sorted(groups))))
        return 2

    sb, ids = build_storyboard(a.root, a.group, groups, gl)
    tl = build_timeline(a.root, a.group, ids, groups)
    ft, toks, miss = build_facts(a.root, a.group, groups[a.group]['rows'])

    res = [('script/storyboard_%s.md' % a.group, sb),
           ('script/timeline_%s.md' % a.group, tl),
           ('research/facts_%s.md' % a.group, ft)]
    tot = 0
    for rel, content in res:
        if content is None:
            continue
        t = toks_text(content)
        tot += t
        print('  %-34s %6d tokens  %d 字符' % (rel, t, len(content)))
        if not a.dry:
            p = os.path.join(a.root, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w', encoding='utf-8').write(content)
    print('  %-34s %6d tokens' % ('合计', tot))
    print('  token 命中 %d 个；未命中 %d 个：%s' % (len(toks), len(miss), ' · '.join(miss[:12])))

    bad = 0
    if a.budget_storyboard and toks_text(sb) > a.budget_storyboard:
        print('⚠ storyboard 超预算：%d > %d' % (toks_text(sb), a.budget_storyboard)); bad = 1
    if a.budget_facts and toks_text(ft) > a.budget_facts:
        print('⚠ facts 超预算：%d > %d' % (toks_text(ft), a.budget_facts)); bad = 1
    return bad


if __name__ == '__main__':
    sys.exit(main())
