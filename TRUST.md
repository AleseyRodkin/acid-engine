# Trust model

AppSec question: why trust Acid Judge itself?

## What the product claims

Acid Judge proves **execution identity**, not that the approved code is safe or
correct. If the approved body is `return amount * 100` and the hash matches,
the verdict is PASS even when the business rule is wrong.

Acid Judge verifies software identity inside a trusted runtime; it does
not establish runtime isolation.

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

- Bytes of the tool file before import (`source_hash`).
- Bytes of the locked callable (AST canon, else bytecode).
- `ArtifactRef` locator hashes (`source_hash` of the file, `body_hash` of the
  entry) compared before import when set.
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
- `os.environ` and other process environment. Implementation identity is
  bytes + CPython minor + canon kind, not the environment the bytes run in.
- Packages in site-packages / the standard library. That is a supply-chain
  control (SBOM / SLSA), not this gate.

## Pre-execution vs post-execution

Hook / `locks --index` bind: the file about to run matches the lock. Not PASS.
The hook hashes `source_hash` before import. A swapped file is deny; top-level code does not run.
Unknown at the hook is deny (not enough facts is not allow). Lookup is exact id or resolved path, not basename.
A patch of any contour file requires re-taking every lock. That is the pin.
`cli.py` is not in the contour: a CLI help-text patch does not reshoot locks.
`judge` with a worker: bind, seal local deps from those bytes, run, observe,
verdict. PASS exists only on this path.

Local deps are sealed against the **locked** `dep:` hash from one read of each
file immediately before run. A write to `helper.py` after that read does not
change what `import helper` sees. An undeclared local import is FAIL.
Sealed modules are keyed per judge context (`acid_dep_<id>_…`), not under a
shared `sys.modules["helper"]` slot — two tools with the same helper name do
not cross.

Symlinks are followed. Identity is the target's bytes. Retarget after lock
is `source_hash` FAIL (the followed path's bytes changed before import).


## Who checks the checker

The Rust binary does not re-implement the hasher. It pins the hasher's
files, then asks Python to identify, then binds, then runs. Swap the
hasher file → `runtime_hash` FAIL before identify.

SLSA answers how an artifact was produced. This product answers which artifact
actually ran. Receipts are execution evidence. They are not a competing
provenance standard.

