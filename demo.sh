#!/usr/bin/env bash
# 60 seconds: honest PASS, then a swapped body is blocked. Not a sandbox.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
SCRIPT=examples/tools/compute_amount.py
PLAN=examples/tools/compute_amount.plan.json
INPUT='{"cents":1999,"qty":2}'

echo "1. approved body"
python -m acid_engine judge --script "$SCRIPT" --plan "$PLAN" --input "$INPUT"

TMP="$(mktemp -d)"
mkdir -p "$TMP/examples/tools"
python3 - "$TMP" <<'PY'
from pathlib import Path
import sys
tmp = Path(sys.argv[1])
src = Path("examples/tools/compute_amount.py").read_text()
(tmp / "examples/tools/compute_amount.py").write_text(
    src.replace("cents * qty", "cents * qty + 1", 1)
)
PY

echo "2. swapped body — must not PASS"
set +e
python -m acid_engine judge --script "$TMP/examples/tools/compute_amount.py" --plan "$PLAN" --input "$INPUT"
code=$?
set -e
if [ "$code" -eq 0 ]; then
  echo "demo failed: tamper was not blocked" >&2
  exit 1
fi
echo "demo: honest PASS, tamper blocked"
