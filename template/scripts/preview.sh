#!/usr/bin/env bash
# 跨平台兼容入口。
# 上游实现是 #!/bin/zsh + rsync + BSD sed，在 Windows/Git Bash 下无法运行，
# 已由同目录下的同名 .py 实现取代；本文件只负责找到可用的 Python 并转发参数。
# 因此 SKILL.md / reference/ 里记录的 `scripts/<name>.sh ...` 调用方式保持有效。
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
BASE="$(basename "$0" .sh)"

find_py() {
  local c
  for c in "$A2E_PYTHON" \
           "$HOME/.venv/a2e/Scripts/python.exe" \
           "$HOME/.venv/a2e/bin/python" \
           python3 python; do
    [ -n "$c" ] || continue
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
      printf '%s' "$c"
      return 0
    fi
  done
  return 1
}

PY="$(find_py)" || { echo "[a2e] 找不到可用的 Python 3.8+（可用 A2E_PYTHON 指定）" >&2; exit 1; }
# Git Bash 下 $HERE 是 /c/... 形式的 MSYS 路径，Windows 版 Python 无法解析（会变成 C:\c\...），
# 必须经 cygpath 转成盘符路径。
HERE_WIN="$HERE"
if command -v cygpath >/dev/null 2>&1; then HERE_WIN="$(cygpath -w "$HERE")"; fi
export PYTHONUTF8=1
exec "$PY" "$HERE_WIN/$BASE.py" "$@"
