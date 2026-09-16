# Reproduce the gate

Not a product tour. Two attacks. Repo files stay clean — copies live in `/tmp`.

Not an MCP gateway. Gateways watch tool *descriptions* on the network. This gate watches *file bytes* of a locally approved Python tool (and of the judge contour) immediately before the call.

Does not catch a shell. Does not sandbox the body after PASS.

Install once (`pip install acid-judge` or `pip install -e ".[dev]"` from this repository). `PYTHONPATH=.` is not needed.

## 1. Swap the tool body

Honest run, cents × qty = 3998:

```bash
acid-judge judge \
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

acid-judge judge \
  --script /tmp/acid-attack/examples/tools/compute_amount.py \
  --plan examples/tools/compute_amount.plan.json \
  --input '{"cents": 1999, "qty": 2}'
```

Code ≠ 0. `source_hash`. No `PASS`. File is not imported. Guard: `tests/integration/test_compute_amount_tamper.py`.

Same drift as a table, still no execution:

```bash
acid-judge diff \
  --script /tmp/acid-attack/examples/tools/compute_amount.py \
  --plan examples/tools/compute_amount.plan.json
```

`DRIFT` is inspection **after** `source_hash` matches. A swapped file fails
`source_hash` first and is not imported — including under `diff`.

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

acid-judge judge \
  --script examples/bones/n_plus_one.json \
  --plan /tmp/bad-canon.plan.json \
  --input '{"n": 3}'
```

Code ≠ 0. `runtime_hash`. No `PASS`. Guard: `tests/integration/test_cli.py::test_cli_judge_runtime_mismatch_fails_before_pass`.

Same class of miss as replacing `implementation_canon.py` on disk after the lock was taken.

## 3. Swap a helper, not the entry

`entry.py` imports `helper.py`. Lock pins `dep:helper.py`. Replace only helper.

Code ≠ 0. `dependency_hash`. No `PASS`. Body does not run. Guard: `tests/integration/test_local_deps.py`.

## 4. Import-time side effect

Top-level code in the tool file is not `implementation`. CLI `judge`, the hook, and the worker hash `source_hash` **before** that file is imported.

```bash
# Honest lock, then prepend a write to the tool file, then judge with the old lock.
acid-judge judge \
  --script examples/tools/compute_amount.py \
  --plan examples/tools/compute_amount.plan.json \
  --input '{"cents": 1999, "qty": 2}'
```

Mismatch → `source_hash`, the file is not imported, no sentinel is created.
Guard: `tests/integration/test_import_time.py`, `tests/integration/test_hook.py`.

## 5. Concurrent same-named helpers

Two approved tools, each with its own `helper.py`. Embed `judge_script` on
threads. A shared `sys.modules["helper"]` slot would PASS the other's body.

Guard: `tests/integration/test_concurrent_helpers.py`.

## What this is not

- Not MCP tool-description scanning.
- Not a sandbox.
- Not `proven_pure`.
- `judge_script` without `toolchain` is SKIPPED, not PASS. Use `judge_script_from_lock`.
