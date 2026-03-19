#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: run_with_style_matlab.sh <script.m>" >&2
  exit 1
fi

SCRIPT_PATH="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STYLE_DIR="$ROOT_DIR/templates/matlab"

if ! command -v matlab >/dev/null 2>&1; then
  echo "matlab not found in PATH" >&2
  exit 2
fi

matlab -batch "addpath('${STYLE_DIR}'); apply_matlab_style; run('${SCRIPT_PATH}');"
