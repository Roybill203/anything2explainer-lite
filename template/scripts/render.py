#!/usr/bin/env python3
"""整片渲染（移植自上游 render.sh）。

用法：python scripts/render.py            # 版本号取环境变量 VER，默认 v1
      VER=v1 scripts/render.sh
产出：renders/<slug>_v1.mp4 + fin_frames/ + renders/sheet_v1.html + render.done
环境变量：CONC 并发（默认 6）、RTIMEOUT（默认 300000）、SKIP_BUNDLE=1 复用 build_full、
          KEEP_BUNDLE=1 保留 build_full。
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _env  # noqa: E402


def main():
    root = _env.package_root()
    ver = os.environ.get('VER', 'v1')
    slug = _env.slug()

    renders = os.path.join(root, 'renders')
    os.makedirs(renders, exist_ok=True)
    mp4 = os.path.join(renders, f'{slug}_{ver}.mp4')

    bundle = os.path.join(root, 'build_full')
    if not (os.environ.get('SKIP_BUNDLE') == '1' and os.path.isdir(bundle)):
        shutil.rmtree(bundle, ignore_errors=True)
        _env.run([_env.exe('npx'), 'remotion', 'bundle', 'src/index.ts',
                  '--out-dir', bundle, '--log=error'], cwd=root, check=True)

    _env.run([_env.exe('npx'), 'remotion', 'render', bundle, 'Video', mp4,
              '--codec=h264', '--crf=16',
              f"--concurrency={os.environ.get('CONC', '6')}",
              f"--timeout={os.environ.get('RTIMEOUT', '300000')}",
              '--log=error'], cwd=root, check=True)

    if not (os.path.isfile(mp4) and os.path.getsize(mp4) > 0):
        raise SystemExit('RENDER FAILED')

    fin = os.path.join(root, 'fin_frames')
    shutil.rmtree(fin, ignore_errors=True)
    os.makedirs(fin, exist_ok=True)
    _env.run([_env.exe('ffmpeg'), '-v', 'error', '-y', '-i', mp4,
              '-q:v', '4', os.path.join(fin, 'f_%04d.jpg')], cwd=root, check=True)

    count = len([f for f in os.listdir(fin) if f.startswith('f_')])
    with open(os.path.join(root, 'fin_count.txt'), 'w', encoding='utf-8') as f:
        f.write(str(count))

    try:
        _env.run([sys.executable, os.path.join(root, 'scripts', 'sheet.py'), fin,
                  os.path.join(renders, f'sheet_{ver}.html'), '60'], cwd=root, check=True)
    except Exception as e:
        print(f'[a2e] sheet.py 失败（不阻断渲染）：{e}')

    if os.environ.get('KEEP_BUNDLE') != '1':
        shutil.rmtree(bundle, ignore_errors=True)
    with open(os.path.join(root, 'render.done'), 'w', encoding='utf-8') as f:
        f.write('done\n')
    print('done')


if __name__ == '__main__':
    _env.safe_stdout()
    main()
