#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
powershell_script="$(cygpath -w "$script_dir/ask-ai-lab.ps1")"

# Keep MSYS from rewriting the Windows path passed to PowerShell.
export MSYS2_ARG_CONV_EXCL='*'
exec powershell.exe \
  -NoProfile \
  -ExecutionPolicy Bypass \
  -File "$powershell_script" \
  "$@"
