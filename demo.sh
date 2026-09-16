#!/usr/bin/env bash
# 60 seconds: honest PASS, then a swapped body is blocked. Not a sandbox.
# Requires CPython 3.11+ and acid-judge installed (`pip install acid-judge`
# or `pip install -e .` from this repository). Does not set PYTHONPATH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! python3 -c "import acid_engine" >/dev/null 2>&1; then
  python3 -m pip install -q -e "$ROOT"
fi

aj() { python3 -m acid_engine "$@"; }

SCRIPT=examples/tools/compute_amount.py
PLAN=examples/tools/compute_amount.plan.json
INPUT='{"cents":1999,"qty":2}'

echo "1. approved body"
aj judge --script "$SCRIPT" --plan "$PLAN" --input "$INPUT"

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
aj judge --script "$TMP/examples/tools/compute_amount.py" --plan "$PLAN" --input "$INPUT"
code=$?
set -e
if [ "$code" -eq 0 ]; then
  echo "demo failed: tamper was not blocked" >&2
  exit 1
fi
echo "demo: honest PASS, tamper blocked"
