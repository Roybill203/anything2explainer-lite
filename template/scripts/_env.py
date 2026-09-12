#!/usr/bin/env python3
"""跨平台公共层（Windows 移植版，随本 skill 副本一起维护）。

背景：上游脚本是 #!/bin/zsh + rsync + BSD sed，在 Windows/Git Bash 下无法运行。
本模块把「可执行文件解析」和「项目元信息读取」集中到这里，供移植后的脚本复用。

关键坑（已实测）：Windows 上 npx/npm 实际是 npx.CMD / npm.CMD，
subprocess.run(['npx', ...]) 会抛 FileNotFoundError [WinError 2]，
必须先经 shutil.which() 解析出完整路径再调用。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 兜底搜索路径：PATH 里找不到时按序尝试（只放系统默认位置，不放任何个人路径；
# 如需指定本机安装位置，请用环境变量 A2E_NODE / A2E_FFMPEG 等）
_FALLBACK_DIRS = [
    os.path.join(os.environ.get('ProgramFiles', r'C:\Program Files'), 'nodejs'),
    os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), 'nodejs'),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'nodejs'),
    '/usr/local/bin',
    '/usr/bin',
    '/opt/homebrew/bin',
]


def exe(name):
    """解析可执行文件路径。Windows 下正确返回 .CMD/.EXE 全路径。"""
    env_key = 'A2E_' + name.upper().replace('-', '_')
    override = os.environ.get(env_key)
    if override and os.path.exists(override):
        return override
    found = shutil.which(name)
    if found:
        return found
    for d in _FALLBACK_DIRS:
        if not d or not os.path.isdir(d):
            continue
        for ext in ('', '.exe', '.EXE', '.cmd', '.CMD', '.bat'):
            cand = os.path.join(d, name + ext)
            if os.path.exists(cand):
                return cand
    raise SystemExit(
        f'[a2e] 找不到可执行文件 {name}。请确认它已安装并在 PATH 中，'
        f'也可用环境变量 {env_key} 直接指定路径。'
    )


def run(args, **kw):
    """subprocess.run 的可移植包装：自动解析 argv[0]。"""
    argv = list(args)
    argv[0] = exe(argv[0])
    return subprocess.run(argv, **kw)


def safe_stdout():
    """把 stdout/stderr 的编码错误降级为替换字符，避免在 cp936 控制台
    因 ✗ / ⚠ / ✓ 等符号抛 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')
        except Exception:
            pass


def winpath(p):
    """把 Git Bash / MSYS 风格路径（/d/a2e/x、/c/Users/x）转成 Windows 形式（D:/a2e/x）。

    坑（2026-09-11 实测）：Python 在 Windows 下不认 MSYS 盘符前缀，
    `os.path.abspath('/d/a2e/fixture')` 会得到 `D:////d////a2e////fixture`（凭空多一层 d），
    脚本会**静默把产物写到错误目录**，而且不报错。凡是接收「输出目录 / 文件路径」参数的
    脚本都应先过这个函数。非 Windows 平台原样返回。
    """
    if os.name != 'nt':
        return p
    m = re.match(r'^/([A-Za-z])(/.*)?$', p or '')
    if m:
        return m.group(1).upper() + ':' + (m.group(2) or '/')
    return p


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def slug():
    cfg = _read(os.path.join(ROOT, 'src', 'config.ts'))
    m = re.search(r"slug:\s*'([^']+)'", cfg)
    if not m:
        raise SystemExit('[a2e] 无法从 src/config.ts 读取 slug')
    return m.group(1)


def total_frames():
    tl = _read(os.path.join(ROOT, 'src', 'common', 'timeline.ts'))
    m = re.search(r'TOTAL_FRAMES\s*=\s*(\d+)', tl)
    if not m:
        raise SystemExit('[a2e] 无法从 src/common/timeline.ts 读取 TOTAL_FRAMES（还没跑过 tts_build.py？）')
    return int(m.group(1))


def fps():
    return 30


def package_root():
    """返回 template/ 目录（脚本所在 scripts/ 的上级）。同时校验目录结构。"""
    if not (os.path.isfile(os.path.join(ROOT, 'src', 'config.ts'))
            and os.path.isdir(os.path.join(ROOT, 'src', 'common'))):
        raise SystemExit(f'[a2e] 找不到模板（{ROOT} 不像 template/），请从 template/scripts/ 里运行本脚本')
    return ROOT
