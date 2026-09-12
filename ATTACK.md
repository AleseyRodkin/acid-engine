# Reproduce the gate

Not a product tour. Two attacks. Repo files stay clean — copies live in `/tmp`.

Not an MCP gateway. Gateways watch tool *descriptions* on the network. This gate watches *file bytes* of a locally approved Python tool (and of the judge contour) immediately before the call.

Does not catch a shell. Does not sandbox the body after PASS.

## 1. Swap the tool body

Honest run, cents × qty = 3998:

```bash
PYTHONPATH=. python -m acid_engine judge \
  --script examples/tools/compute_amount.py \
  --plan examples/tools/compute_amount.plan.json \
  --input '{"cents": 1999, "qty": 2}'
```

Code 0, `PASS`, `runtime: pinned`.

Same lock, swapped formula (`cents * qty + 1` in a copy). Keep the copy two directories deep — the example script looks up the repo root via `Path(__file__).parents[2]`.

```bash
mkdir -p /tmp/acid-attack/examples/tools
python3 - << 'PY'
from pathlib import Path
src = Path("examples/tools/compute_amount.py").read_text()
Path("/tmp/acid-attack/examples/tools/compute_amount.py").write_text(
    src.replace("cents * qty", "cents * qty + 1", 1)
)
PY

PYTHONPATH=. python -m acid_engine judge \
  --script /tmp/acid-attack/examples/tools/compute_amount.py \
  --plan examples/tools/compute_amount.plan.json \
  --input '{"cents": 1999, "qty": 2}'
```

Code ≠ 0. `module_hash`. No `PASS`. Body does not run. Guard: `tests/integration/test_compute_amount_tamper.py`.

## 2. Swap the hasher, not the tool

CLI `judge --plan` pins `runtime_hashes` (worker, python_runtime, runner, implementation_canon) before run.

Poison only the expected hash of the canon file. Live files stay honest. The lock no longer matches the contour:

```bash
python3 - << 'PY'
import json
from pathlib import Path
raw = json.loads(Path("examples/bones/n_plus_one.plan.json").read_text())
raw["toolchain"]["runtime_hashes"][
    "acid_engine/level2/implementation_canon.py"
] = "0" * 64
Path("/tmp/bad-canon.plan.json").write_text(json.dumps(raw))
PY

PYTHONPATH=. python -m acid_engine judge \
  --script examples/bones/n_plus_one.json \
  --plan /tmp/bad-canon.plan.json \
  --input '{"n": 3}'
```

Code ≠ 0. `runtime_hash`. No `PASS`. Guard: `tests/integration/test_cli.py::test_cli_judge_runtime_mismatch_fails_before_pass`.

Same class of miss as replacing `implementation_canon.py` on disk after the lock was taken.

## What this is not

- Not MCP tool-description scanning.
- Not a sandbox.
- Not `proven_pure`.
- Library `judge_script` without toolchain still does not pin the contour. The README command does.
