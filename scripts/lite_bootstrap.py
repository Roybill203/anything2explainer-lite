#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lite_bootstrap.py —— 用**本 skill 自带的引擎**起一个新项目

本 skill 是**完全独立**的：引擎、示例、参考文档、脚本全部自带，
下载本 skill 即可使用，**不需要安装 anything2explainer 主 skill**。

本脚本做四件事：
  1. 前置检查（引擎 / 示例 / 协议文档是否齐全）——缺件早失败，不会跑到一半才发现
  2. 跑自带引擎的 `template/scripts/new_project.py <目标目录> <slug>`
     （复制模板 → npm install → tsc --noEmit）
  3. 把 lite 的协议文档拷进项目的 `reference/`
  4. 生成 `reference/api-index.md`（图元签名索引，ui+fx 15.6K → 1.3K）

用法：
  python lite_bootstrap.py <目标目录> <slug> [--skip-install] [--no-api-index]
  python lite_bootstrap.py --check          # 只做独立性自检，不建项目

例：
  python lite_bootstrap.py D:/a2e/my-video myvideo

退出码：0 成功；1 前置检查失败（自带件缺失 / 参数错）；2 建项目失败。

可选覆盖（一般不需要）：
  A2E_ENGINE=<template 目录>  改用外部引擎（仅用于开发期对比/调试）
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LITE_ROOT = os.path.dirname(HERE)

# 自带引擎：本 skill 的 template/
OWN_ENGINE = os.path.join(LITE_ROOT, 'template')

# 引擎里必须存在的文件（前置检查，缺一个就早失败）
ENGINE_REQUIRED = [
    'package.json',
    'tsconfig.json',
    'src/config.ts',
    'src/common/types.ts',
    'src/ui.tsx',
    'src/fx.tsx',
    'scripts/new_project.py',
    'scripts/_env.py',
    'scripts/still.py',
    'scripts/motion_check.py',
    'scripts/selfcheck.py',
    'scripts/frame_metrics.py',
    'scripts/gen_api_index.py',
    'scripts/slice.py',
    'scripts/zorder_audit.py',      # lite 门禁轴 2
    'scripts/lite_gate.py',         # lite 门禁总入口
    'public/fonts/NotoSansSC.ttf',
]

# lite 协议文档 → 装进项目的 reference/
LITE_DOCS = ['build-contract-lite.md', 'qc-lite.md', 'prompts-lite.md', 'lessons-lite.md']

# 本 skill 必须自带的其余资产（缺失只警告，不阻断）
SOFT_ASSETS = [
    ('examples/rag/shots_src', '示例镜头源码（构建契约 §11 模式路由的落点）'),
    ('examples/rag/frames', '示例参考帧（质量标尺）'),
    ('examples/contrast', '反例对照（审美判据）'),
    ('reference/style-guide.md', '画风/安全区/调色板/图元目录'),
    ('reference/motion-vocabulary.md', '动效帧数与运镜预算'),
    ('reference/composition-and-light.md', '主体尺寸/光/高光时刻/持续动作判据'),
    ('reference/narration-storyboard.md', '解说词/配音/字幕切块/分镜令牌'),
    ('reference/research-brief.md', '研究员 prompt 与事实规则'),
    ('LICENSE', '上游授权（模板内含 OFL 字体）'),
    ('CITATION.cff', '上游引用信息'),
]


def winpath(p):
    """把 MSYS 风格 /d/x 或 /c/Users/... 归一成 D:/x / C:/Users/...
    在 Windows 上 os.path.abspath('/d/x') 会变成 D:/d/x（静默进错目录）。"""
    if os.name != 'nt':
        return p
    m = re.fullmatch(r'/([A-Za-z])/(.*)', p.replace('\\', '/'))
    if m:
        return f'{m.group(1).upper()}:/{m.group(2)}'
    return p


def preflight(verbose=True):
    """返回 (engine_dir, errors, warnings)。engine_dir 为 None 表示不可用。"""
    errors, warns = [], []
    override = os.environ.get('A2E_ENGINE')
    if override:
        engine = os.path.abspath(winpath(override))
        src = 'A2E_ENGINE 覆盖'
    else:
        engine = os.path.abspath(OWN_ENGINE)
        src = '本 skill 自带'

    if not os.path.isdir(engine):
        errors.append(f'引擎目录不存在：{engine}（{src}）')
        if verbose:
            print(f'[lite] 引擎来源：{src}  →  {engine}')
        return None, errors, warns

    missing = [f for f in ENGINE_REQUIRED if not os.path.exists(os.path.join(engine, f))]
    if missing:
        errors.append(f'引擎缺件（{engine}）：{", ".join(missing)}')

    for rel, why in SOFT_ASSETS:
        if not os.path.exists(os.path.join(LITE_ROOT, rel)):
            warns.append(f'缺 {rel}（{why}）')
    for d in LITE_DOCS:
        if not os.path.isfile(os.path.join(LITE_ROOT, 'reference', d)):
            errors.append(f'缺协议文档 reference/{d}')

    if verbose:
        print(f'[lite] 引擎来源：{src}  →  {engine}')
        print(f'[lite] 自带件检查：{"✓ 全部就位" if not errors else "✗ 缺 " + str(len(errors)) + " 项"}')
        for w in warns:
            print(f'[lite]   ⚠ {w}')
    return (None if errors else engine), errors, warns


def main():
    argv = sys.argv[1:]
    if '--check' in argv:
        engine, errors, _ = preflight()
        for e in errors:
            print(f'[lite] ✗ {e}')
        print('[lite] ' + ('独立性自检通过 ✓' if engine else '独立性自检不通过 ✗'))
        return 0 if engine else 1

    args = [a for a in argv if not a.startswith('--')]
    if len(args) < 2:
        print(__doc__)
        return 1
    dest = os.path.abspath(winpath(args[0]))
    slug = args[1]

    engine, errors, _ = preflight()
    if engine is None:
        for e in errors:
            print(f'[lite] ✗ {e}')
        print('[lite] → 本 skill 是自带引擎的独立包，出现此错说明安装不完整（请重新获取本 skill）。')
        return 1

    np_ = os.path.join(engine, 'scripts', 'new_project.py')
    env = dict(os.environ)
    if '--skip-install' in argv:
        env['SKIP_INSTALL'] = '1'
    print(f'[lite] 建项目：{dest}（slug={slug}）')
    r = subprocess.run([sys.executable, np_, dest, slug], env=env)
    if r.returncode != 0:
        print('[lite] ✗ 建项目失败。')
        return 2

    # 装 lite 协议文档
    ref = os.path.join(dest, 'reference')
    os.makedirs(ref, exist_ok=True)
    copied = []
    for name in LITE_DOCS:
        s = os.path.join(LITE_ROOT, 'reference', name)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(ref, name))
            copied.append(name)
    print(f'[lite] 协议文档 → reference/：{", ".join(copied) or "(无)"}')

    # 图元签名索引（需要 node/tsc 环境，失败不致命）
    if '--no-api-index' not in argv:
        gai = os.path.join(dest, 'scripts', 'gen_api_index.py')
        out = os.path.join(ref, 'api-index.md')
        print(f'[lite] $ python scripts/gen_api_index.py {dest} --out {out}')
        r = subprocess.run([sys.executable, gai, dest, '--out', out, '--budget', '1500'], cwd=dest)
        if r.returncode != 0:
            print('[lite] ⚠ api-index 生成失败（不影响开工，源码改动后可重跑）')

    print()
    print('[lite] ✓ 就绪。下一步：')
    print(f'       1) 读 {os.path.join(ref, "build-contract-lite.md")} 并据此派单（模板见 reference/prompts-lite.md）')
    print('       2) 派单前跑：python scripts/slice.py <项目根> --group Gn')
    print('       3) 每组收组前跑：python scripts/zorder_audit.py src/shots --gate')
    print('       4) 成片后跑：python scripts/lite_gate.py --require-final')
    return 0


if __name__ == '__main__':
    sys.exit(main())
