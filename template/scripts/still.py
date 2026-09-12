#!/usr/bin/env python3
"""出 still（移植自上游 still.sh）。

用法：python scripts/still.py <Comp> <帧号列表> <输出目录> [tag]
      Comp: Video | Overlay | G1..G8；帧号 1 起、逗号分隔；输出目录建议用绝对路径。

⚠ 每个构建组只用一个 tag（如 g3），改代码后删掉 build_dev_<tag> 再跑；
  不要每次换新 tag（每个 bundle 约 40MB）。
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _env  # noqa: E402


def main():
    if len(sys.argv) < 4:
        raise SystemExit('usage: still.py <Comp> <frames 1-based csv> <out_dir> [tag]')
    root = _env.package_root()
    comp, frames_arg, out = sys.argv[1], sys.argv[2], os.path.abspath(_env.winpath(sys.argv[3]))
    tag = sys.argv[4] if len(sys.argv) > 4 else comp

    bundle = os.path.join(root, f'build_dev_{tag}')
    if not os.path.isdir(bundle):
        _env.run([_env.exe('npx'), 'remotion', 'bundle', 'src/index.ts',
                  '--out-dir', bundle, '--log=error'], cwd=root, check=True)

    os.makedirs(out, exist_ok=True)
    npx = _env.exe('npx')
    frames = [f.strip() for f in frames_arg.split(',') if f.strip()]
    # 压缩档（C1/C2+）出小图：STILL_SCALE=0.25 → 320×180。构图检查够用；
    # 只有要确认文字时才出 1 张全尺寸（不设 STILL_SCALE 即 1.0）。
    scale = os.environ.get('STILL_SCALE', '').strip()
    for item in frames:
        n = int(item)
        dst = os.path.join(out, 'f_%04d.png' % n)
        cmd = [npx, 'remotion', 'still', bundle, comp, dst, f'--frame={n - 1}', '--log=error']
        if scale:
            cmd.append('--scale=%s' % scale)
        _env.run(cmd, cwd=root, check=True)

    # 清理 4 小时以上没动过的 remotion 临时 bundle（只清明显已死的：这台机器上可能有
    # 别的 remotion 项目/agent 正在渲染，短阈值会删掉别人正在用的 bundle）。CLEAN_TMP=0 可关闭。
    if os.environ.get('CLEAN_TMP', '1') == '1':
        tmp = os.environ.get('TMPDIR') or os.environ.get('TEMP') or '/tmp'
        cutoff = time.time() - 240 * 60
        try:
            for name in os.listdir(tmp):
                if not name.startswith('remotion-webpack-bundle-'):
                    continue
                p = os.path.join(tmp, name)
                try:
                    if os.path.getmtime(p) < cutoff:
                        shutil.rmtree(p, ignore_errors=True)
                except OSError:
                    pass
        except OSError:
            pass

    print(len([f for f in os.listdir(out) if f.startswith('f_')]))


if __name__ == '__main__':
    _env.safe_stdout()
    main()
