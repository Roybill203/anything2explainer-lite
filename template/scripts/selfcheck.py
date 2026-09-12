#!/usr/bin/env python3
"""主会话静态自检（不渲染，几秒跑完；与 QC 从像素查互补）：
  0) 分镜表一致：生成物 分镜表.md 与源 storyboard_src.md 对账（防「手改生成物」被下次重生成抹掉）；
  1) 帧覆盖：各组 index.ts 里的 {id, from, to} 与 分镜表.md 的镜头区间对账，报空洞 / 重叠 / 缺失；
  2) 闪烁白名单：每个 SCxx.tsx 里 GlitchIn 的出现次数 vs 分镜表全局约束 §3 白名单；
  3) 画面字面量：抽取各 SC 文件里会上画面的字符串，剔除 CSS / 标识符噪声，列出不在事实清单里的词供人工核对。
用法：python3 scripts/selfcheck.py [G1 G2 …]（不传则查全部已建组）"""
import re, os, sys, glob
try:
    import _env; _env.safe_stdout()   # Windows 移植层：避免 ✗ 等符号在 cp936 控制台抛 UnicodeEncodeError
except ImportError:
    pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sb = open(f'{ROOT}/分镜表.md', encoding='utf-8').read()

# ---- 分镜表镜头区间 ----
sb_shots = {}
for m in re.finditer(r'^\| (SC\d\d)[^|]*\| (\d+)–(\d+) \|', sb, re.M):
    sb_shots[m.group(1)] = (int(m.group(2)), int(m.group(3)))

# ---- 白名单 ----
# 支持两种惯例（两种都合法，此前只认 A，凡用 B 的影片会整片误报 ✗）：
#   A) 枚举式——分镜表写「**闪烁白名单**：SC01 词 · SC02 词。**不在表内…」
#   B) 内联式——在每镜头「动效」列直接用 `GlitchIn` / "glitch" 标出该镜头重点词
wl_text = re.search(r'\*\*闪烁白名单.*?\*\*：(.*?)。\*\*不在表内', sb, re.S)
whitelist = {}
if wl_text:
    for part in wl_text.group(1).split('·'):
        mm = re.match(r'\s*(SC\d\d)\s+(.*)', part.strip())
        if mm: whitelist[mm.group(1)] = mm.group(2).strip()
if not whitelist:  # 内联式
    for line in sb.splitlines():
        mm = re.match(r'\|\s*(SC\d\d)\b', line)
        if not mm or not re.search(r'GlitchIn|glitch', line):
            continue
        sid = mm.group(1)
        pre = line[:line.index('GlitchIn')] if 'GlitchIn' in line else line
        w = re.findall(r'[「『]([^」』]{1,24})[」』]', pre)
        whitelist[sid] = w[-1] if w else '（内联标注）'
    if whitelist:
        print(f'[glitch] 按内联惯例从「动效」列反推白名单（{len(whitelist)} 条）')

groups = sys.argv[1:] or sorted(os.path.basename(p) for p in glob.glob(f'{ROOT}/src/shots/G*'))
problems = 0

# ---- 0) 源/生成物一致性：分镜表.md 是 script/storyboard_src.md 的函数 ----
# render_storyboard.py 只做一件事：把源里的 {S07.from-8} 令牌换成帧号。
# 若有人在**生成物**上直接改规格（很容易发生，尤其是补「规格修正」留痕时），
# 下一次重生成会把它默默抹掉 —— 这里复算一遍，逐行报脱节。
def check_drift():
    sp, tlp = f'{ROOT}/script/storyboard_src.md', f'{ROOT}/script/timeline.json'
    if not (os.path.exists(sp) and os.path.exists(tlp)):
        return 0
    import json
    d = json.load(open(tlp, encoding='utf-8'))
    S = {s['id']: s for s in d['sentences']}
    C = {c['n']: c['from'] for c in d['chapters']}

    def rep(m):
        k, f, off = m.group(1), m.group(2), int(m.group(3) or 0)
        if k == 'TOTAL':
            v = d['total_frames']
        elif k.startswith('C'):
            v = C[int(k[1:])]
        else:
            s = S[k]
            if f == 'from': v = s['from']
            elif f == 'to': v = s['to']
            elif f and f.startswith('c'): v = s['subs'][int(f[1:]) - 1]['from']
            else: return m.group(0)
        return str(v + off)

    fresh = re.sub(r'\{(S\d\d|C\d|TOTAL)(?:\.(from|to|c\d+))?([+-]\d+)?\}',
                   rep, open(sp, encoding='utf-8').read()).splitlines()
    disk = sb.splitlines()
    n = min(len(fresh), len(disk))
    bad = [i + 1 for i in range(n) if fresh[i] != disk[i]]
    if len(fresh) != len(disk):
        bad += list(range(n + 1, max(len(fresh), len(disk)) + 1))
    if bad:
        print(f'[drift] ✗ 分镜表.md 有 {len(bad)} 行与 storyboard_src.md 不一致（含第 {bad[0]}…{bad[-1]} 行）')
        print('        → 规格只改 script/storyboard_src.md，改完跑 render_storyboard.py 重生成；')
        print('          不要在生成物上直接改 —— 那样下一次重生成会静默抹掉，留痕同样丢。')
        return 1
    print('[drift] 分镜表.md 与 storyboard_src.md 一致 ✓')
    return 0

problems += check_drift()

# 只检查「真的建了镜头」的组：模板 new_project 会建 G1–G8 八个组目录，
# 影片若只用 3 组，剩下 5 个空脚手架（只有 index.ts/Preview.tsx）会让下面的
# coverage 逐条刷「没有字面量 from/to」——每部片都会误报 5 条噪声。
groups = [g for g in groups if glob.glob(f'{ROOT}/src/shots/{g}/SC*.tsx')]

# ---- 1) 帧覆盖 ----
built = {}
for g in groups:
    idx = f'{ROOT}/src/shots/{g}/index.ts'
    if not os.path.exists(idx): continue
    src = open(idx, encoding='utf-8').read()
    for m in re.finditer(r"id:\s*'([^']+)'\s*,\s*from:\s*(\d+)\s*,\s*to:\s*(\d+)", src):
        built[m.group(1)] = (int(m.group(2)), int(m.group(3)), g)
    if not re.search(r"id:\s*'", src):
        print(f'[coverage] {g}: index.ts 里没有字面量 from/to（可能用了常量）→ 请人工核对')
print(f'[coverage] 分镜表 {len(sb_shots)} 镜头；已建 {len(built)} 镜头')
for sid, (a, b) in sorted(sb_shots.items()):
    if sid in built:
        ba, bb, g = built[sid]
        if (ba, bb) != (a, b):
            print(f'  ✗ {sid} ({g}) 区间 {ba}–{bb} ≠ 分镜表 {a}–{b}'); problems += 1
import json
_tl = json.load(open(f'{ROOT}/script/timeline.json'))
_chapter_starts = {c['from'] for c in _tl['chapters']}
ids = sorted(built, key=lambda k: built[k][0])
for p, q in zip(ids, ids[1:]):
    gap = built[q][0] - built[p][1]
    # 章节卡占位（上一章末句 to+3 → 本章首句 from−9）是设计上的空洞，跳过
    if gap > 1 and any(built[q][0] == cs - 8 for cs in _chapter_starts):  # 下一镜头首帧 = 本章首句 from−8
        print(f'  · 章节卡空档 {p}→{q}: {built[p][1]}→{built[q][0]}（覆盖层接管）'); continue
    if gap > 1: print(f'  ✗ 空洞 {p}→{q}: {built[p][1]}→{built[q][0]} ({gap-1} 帧无镜头)'); problems += 1
    if gap < -4: print(f'  ✗ 重叠 {p}→{q}: {-gap+1} 帧'); problems += 1

# ---- 2) 闪烁 ----
print(f'[glitch] 白名单 {len(whitelist)} 条')
for g in groups:
    for f in sorted(glob.glob(f'{ROOT}/src/shots/{g}/SC*.tsx')):
        sid = os.path.basename(f)[:4]
        src = open(f, encoding='utf-8').read()
        n = len(re.findall(r'<GlitchIn\b', src)) + len(re.findall(r'glitchOpacity\(', src))
        want = 1 if sid in whitelist else 0
        flag = '' if n == want else '  ✗'
        if n != want: problems += 1
        print(f'  {sid} GlitchIn×{n} (白名单 {whitelist.get(sid, "—")}){flag}')

# ---- 3) 字面量 ----
fact = re.search(r'1\. \*\*事实清单.*?\n', sb, re.S)
fact_txt = (fact.group(0) if fact else '') + sb  # 分镜表全文都算"已核"（画面文本按分镜写）
noise = re.compile(r'^(#|rgb|[0-9.\s%pxem-]+$|[a-z][A-Za-z0-9-]*$|\.\./|src/|[A-Z_]+$|none|auto|absolute|relative|center|left|right|top|bottom|solid|dashed|round|butt|square|nowrap|hidden|visible|inherit|bold|italic|normal)')
# 字体名（从 public/fonts 反推）不是"画面字符串"
_fd = f'{ROOT}/public/fonts'
FONTS = ({os.path.splitext(f)[0].lower().replace('-', '').replace('_', '').replace(' ', '')
          for f in os.listdir(_fd)} if os.path.isdir(_fd) else set())
print('[literals] 不在分镜表/事实清单中的画面字符串（人工核对）：')
seen = set()
for g in groups:
    for f in sorted(glob.glob(f'{ROOT}/src/shots/{g}/*.tsx')):
        src = open(f, encoding='utf-8').read()
        for s in re.findall(r"(?:'|\"|`)([^'\"`\n]{3,80})(?:'|\"|`)", src):
            s2 = s.strip()
            if not s2 or noise.match(s2) or s2 in seen: continue
            if re.search(r'[{}<>;=]', s2): continue          # JSX 属性片段（引号跨行误抓），非画面文本
            if re.match(r'^[,\s]*[A-Za-z-]+\s*:', s2): continue  # 同上：`, transformOrigin:` 之类
            if s2.replace(' ', '').lower() in FONTS: continue  # 字体名
            if '${' in s2 or 'px' in s2 or 'rgba' in s2 or 'gradient' in s2 or re.fullmatch(r'[\d.,\s]+', s2) or s2.startswith('./') or re.match(r'^[a-zA-Z-]+\(', s2) or s2 in ('border-box','content-box'): continue  # CSS / 模板串 / 路径噪声
            if re.fullmatch(r'[\d.,×x%+\-–\s]+', s2): pass  # 数字类一律列出
            elif not re.search(r'[A-Za-z]{3}', s2): continue
            if s2 in fact_txt or s2 in sb: continue
            seen.add(s2); print(f'  {os.path.basename(f)}: {s2}')
print(f'\nproblems: {problems}')
# 退出码可用于流水线门禁（原版恒为 0，脚本里 grep 不到就无法判成败）
sys.exit(1 if problems else 0)
