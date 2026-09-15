# Interop (0.2.x)

Acid Judge is an **execution-integrity primitive**, not a control plane.

Policy engines ask whether an action is allowed. Sandboxes ask what a process
may touch. MCP scanners ask whether a tool description is poisoned. This
component asks one question:

> Was the implementation that executed the implementation that was approved?

Python is the first adapter. Not the category.

## Where it sits

```text
agent
  → policy / authorization     ("allowed?")
  → Acid Judge                 ("approved implementation?")
  → runtime / sandbox
  → observation / receipt
```

Do not replace APort, Microsoft AGT, Snyk, SLSA, or a sandbox. Call this
layer from them.

## Four stable surfaces

| Surface | Contract |
| --- | --- |
| CLI | `lock` / `judge` / `locks` / `diff` / `receipt` — [COMPATIBILITY.md](COMPATIBILITY.md) |
| Library | `judge_script_from_lock`, `judge_script`, `lock_for_script`, `build_receipt` |
| Hook | Claude Code PreToolUse bind only. Pre ≠ PASS. One harness. |
| Receipt | `acid.receipt.v1`. Extra keys ignored. Optional `context`. |

No APort / AGT / Copilot / MCP adapter in 0.2. Those wait on a caller.

## Embed

```python
from acid_engine import build_receipt, judge_script_from_lock, lock_for_script

result = judge_script_from_lock(script, data, "tool.plan.json")
receipt = build_receipt(
    script, data, result,
    plan=plan,
    toolchain=raw,
    context={"agent": "claude-code", "repository": "acme/payments"},
)
```

`context` is attribution for a future evidence store. It is not identity.
Missing context does not change PASS / FAIL / SKIPPED.

## Not in this contract

Second language, sandbox, MCP suite, dashboard, IAM, hosted registry.
