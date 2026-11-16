#!/usr/bin/env bash
# Interactive, prepared local V1 deployment only. Never enable shell tracing here.
set -euo pipefail
set +x
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${V1_DEMO_PYTHON:-$HOME/.local/share/qa-sdv-v1/runtime/venv-3.12/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  echo "Missing $PYTHON. Follow scripts/v1_acceptance/README.md persistent Python setup; no installation was attempted." >&2
  exit 2
fi
cd "$ROOT"
exec "$PYTHON" -B scripts/v1_demo.py "$@"
