# Trust model

AppSec question: why trust Acid Judge itself?

## What the product claims

Acid Judge proves **execution identity**, not that the approved code is safe or
correct. If the approved body is `return amount * 100` and the hash matches,
the verdict is PASS even when the business rule is wrong.

Root of trust for the supervisor path:

```text
ROOT OF TRUST
      │
      ▼
Rust supervisor  (does not hash the tool body)
      │
      ├── runtime_hashes / worker_hash   (Python contour)
      ├── canonicalization identity      (implementation_canon)
      └── lock (module_hashes + static dep:)
              │
              ▼
          Python tool body
```

CLI-only path (`acid-judge` without the binary) trusts the same Python
contour in-process. That is a smaller TCB story: the process that judges
is the process that can be swapped. Use the supervisor when that matters.

## In the TCB

- Bytes of the locked callable (AST canon, else bytecode).
- Static local `.py` imports (`dep:`).
- Judge contour in `runtime_hashes` (7 files).
- `python_version` / `canon_kind` next to identity.
- Ed25519 of a receipt, local keys.

## Not in the TCB

- The approved tool's behavior after PASS (fs / net / process).
- Shell the agent starts outside `judge`.
- `importlib` / `exec` / `eval` (lock warns; not pinned).
- `Policy.pure` (declared, not instrumented).
- `interface_contract_hash` (derived from the same JSON as `module_hashes`).
- Semantic / business correctness.
- OS, kernel, hardware.

## Who checks the checker

The Rust binary does not re-implement the hasher. It pins the hasher's
files, then asks Python to identify, then binds, then runs. Swap the
hasher file → `runtime_hash` FAIL before identify.

Reproduce: [ATTACK.md](ATTACK.md) §2, [attacks/](attacks/README.md).
