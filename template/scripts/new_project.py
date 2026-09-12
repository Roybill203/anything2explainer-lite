#!/usr/bin/env python3
"""从模板创建新项目（移植自上游 new_project.sh）。

用法：python scripts/new_project.py <目标目录> <slug>
      scripts/new_project.sh <目标目录> <slug>      # 兼容入口

与原版的差异：用 shutil.copytree 替代 rsync，用 Python 改写 config.ts 里的 slug
替代 BSD `sed -i ''`，其余行为一致（含 npm install 与 tsc 校验）。
环境变量：SKIP_INSTALL=1 只复制不装依赖（自检/调试用）。
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _env  # noqa: E402

EXCLUDE = shutil.ignore_patterns(
    'node_modules', 'build*', 'renders', 'fin_frames', 'stills', 'audio', '*.log'
)


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: new_project.py <dest_dir> <slug>')
    src = _env.package_root()
    dest = os.path.abspath(sys.argv[1])
    slug = sys.argv[2] if len(sys.argv) > 2 else 'video'

    if not re.fullmatch(r'[A-Za-z0-9_-]+', slug or ''):
        raise SystemExit(f"slug 只能用字母/数字/-/_，收到：{slug}")

    os.makedirs(dest, exist_ok=True)
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore=EXCLUDE)

    cfg_path = os.path.join(dest, 'src', 'config.ts')
    cfg = open(cfg_path, encoding='utf-8').read()
    cfg2 = re.sub(r"slug:\s*'[^']*'", f"slug: '{slug}'", cfg, count=1)
    if cfg2 == cfg:
        raise SystemExit('[a2e] 未能在 src/config.ts 中找到 slug: \'demo\' 以替换')
    open(cfg_path, 'w', encoding='utf-8', newline='\n').write(cfg2)

    for sub in (f'public/assets/{slug}', 'script', 'research', 'qc', 'stills', 'renders'):
        os.makedirs(os.path.join(dest, sub), exist_ok=True)

    if os.environ.get('SKIP_INSTALL') == '1':
        print(f'project scaffolded (skip install): {dest} (slug={slug})')
        return

    if len(dest) > 90:
        print(f'[a2e] 注意：目标路径较长（{len(dest)} 字符），Windows 下 node_modules '
              f'深层目录可能触发 MAX_PATH 限制。建议把项目放到盘根附近的短路径。')

    print(f'[a2e] npm install（首次约数百 MB，请耐心）…')
    _env.run([_env.exe('npm'), 'install', '--silent', '--no-audit', '--no-fund'],
             cwd=dest, check=True)
    print('[a2e] tsc --noEmit 类型校验…')
    _env.run([_env.exe('npx'), 'tsc', '--noEmit'], cwd=dest, check=True)
    print(f'project ready: {dest} (slug={slug})')


if __name__ == '__main__':
    _env.safe_stdout()
    main()
