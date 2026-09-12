#!/usr/bin/env python3
"""30 帧测渲测 fps（移植自上游 test_render.sh）。

用法：python scripts/test_render.py <Comp> <起始帧 1 起> [tag]
正常 30 帧 3–12 s；<3 fps 要查滤镜/DOM。
"""
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _env  # noqa: E402


def main():
    if len(sys.argv) < 3:
        raise SystemExit('usage: test_render.py <Comp> <start_frame 1-based> [tag]')
    root = _env.package_root()
    comp = sys.argv[1]
    a = int(sys.argv[2])
    tag = sys.argv[3] if len(sys.argv) > 3 else comp

    bundle = os.path.join(root, f'build_dev_{tag}')
    if not os.path.isdir(bundle):
        _env.run([_env.exe('npx'), 'remotion', 'bundle', 'src/index.ts',
                  '--out-dir', bundle, '--log=error'], cwd=root, check=True)

    # 模板里不能带点：Remotion 会把 .XXXXXX 当成图片序列的扩展名而拒渲
    out = tempfile.mkdtemp(prefix=f'explainer_test_{tag}_')
    try:
        t0 = time.perf_counter()
        _env.run([_env.exe('npx'), 'remotion', 'render', bundle, comp, out,
                  '--sequence', '--image-format=jpeg',
                  f'--frames={a - 1}-{a + 28}', '--log=error'], cwd=root, check=True)
        dt = time.perf_counter() - t0
        n = len(os.listdir(out))
        print(f'{n} frames in {dt:.1f}s ({n / dt:.1f} fps)')
    finally:
        shutil.rmtree(out, ignore_errors=True)


if __name__ == '__main__':
    _env.safe_stdout()
    main()
