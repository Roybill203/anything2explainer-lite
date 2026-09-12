#!/usr/bin/env python3
"""前 N 秒样片（移植自上游 preview.sh）——确认点 4：先给用户看风格，别等整片渲完。

用法：python scripts/preview.py [秒数=30] [起始秒=0]
      scripts/preview.sh 30
产出：renders/<slug>_preview_<a>-<b>s.mp4（含配音/字幕/进度条；还没建的组是空画面，正常）
环境变量：CONC 并发（默认 6）、RTIMEOUT（默认 300000）、SKIP_BUNDLE=1 复用 build_prev、
          KEEP_BUNDLE=1 保留 build_prev。
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _env  # noqa: E402


def main():
    root = _env.package_root()
    fps = _env.fps()
    sec = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    frm = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    slug = _env.slug()
    total = _env.total_frames()

    a = frm * fps
    b = a + sec * fps - 1
    if b > total - 1:
        b = total - 1

    renders = os.path.join(root, 'renders')
    os.makedirs(renders, exist_ok=True)
    outf = os.path.join(renders, f'{slug}_preview_{frm}-{frm + sec}s.mp4')

    bundle = os.path.join(root, 'build_prev')
    if not (os.environ.get('SKIP_BUNDLE') == '1' and os.path.isdir(bundle)):
        shutil.rmtree(bundle, ignore_errors=True)
        _env.run([_env.exe('npx'), 'remotion', 'bundle', 'src/index.ts',
                  '--out-dir', bundle, '--log=error'], cwd=root, check=True)

    _env.run([_env.exe('npx'), 'remotion', 'render', bundle, 'Video', outf,
              '--codec=h264', '--crf=18', f'--frames={a}-{b}',
              f"--concurrency={os.environ.get('CONC', '6')}",
              f"--timeout={os.environ.get('RTIMEOUT', '300000')}",
              '--log=error'], cwd=root, check=True)

    if not (os.path.isfile(outf) and os.path.getsize(outf) > 0):
        raise SystemExit('PREVIEW FAILED')

    if os.environ.get('KEEP_BUNDLE') != '1':
        shutil.rmtree(bundle, ignore_errors=True)
    print(outf)


if __name__ == '__main__':
    _env.safe_stdout()
    main()
