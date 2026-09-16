# Tutorial

This is not the law. The live contour is [README.md](README.md). Do not rewrite METHOD from this file.

Demo: lock a body, run `judge`, swap the formula, see FAIL and a receipt.

Install once (`pip install acid-judge` or, from this repository, `pip install -e ".[dev]"`). Then `acid-judge` is on `PATH`. `PYTHONPATH=.` is not needed.

## 1. Bones with `--plan`

From the repository root:

```bash
acid-judge judge \
  --script examples/bones/n_plus_one.json \
  --plan examples/bones/n_plus_one.plan.json \
  --input '{"n": 3}' \
  --receipt /tmp/bones.receipt.json
```

Exit 0, PASS, `{n: 4}`. Receipt has no `proven_pure`.

Without `--plan` this is not a verdict:

```bash
acid-judge judge \
  --script examples/bones/n_plus_one.json \
  --input '{"n": 3}'
```

Exit ≠ 0, SKIPPED. Self-lock is not PASS.

## 2. Lock `compute_amount`

Formula: `cents * qty`. Input `{"cents": 1999, "qty": 2}` → `{"cents": 3998}`.

```bash
acid-judge lock \
  --script examples/tools/compute_amount.py \
  --out examples/tools/compute_amount.plan.json
```

`lock` writes lock JSON; it does not set PASS.

Honest run:

```bash
acid-judge judge \
  --script examples/tools/compute_amount.py \
  --plan examples/tools/compute_amount.plan.json \
  --input '{"cents": 1999, "qty": 2}' \
  --receipt /tmp/amount-ok.receipt.json
```

PASS, `{"cents": 3998}`.

## 3. Swap the body

In `examples/tools/compute_amount.py` replace `cents * qty` with `cents * qty + 1`. Do not touch the JSON or `plan.json`.

```bash
acid-judge judge \
  --script examples/tools/compute_amount.py \
  --plan examples/tools/compute_amount.plan.json \
  --input '{"cents": 1999, "qty": 2}' \
  --receipt /tmp/amount-bad.receipt.json
```

FAIL `module_hash`. The body does not run. Receipt status FAIL, `property`: `module_hash`. Do not re-take the plan for the new body — that is a different lock.

Restore `cents * qty`. Do not commit a broken body.

## What is not here

Graphs, `run` without `--plan` as success, `judge_script` / Pipeline / Composite without a plan+iface pair, semantics via a raw `run_script`, levels 0–4.
