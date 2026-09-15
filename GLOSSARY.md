# Glossary

- **lock** — JSON lock on a body. Not a verdict.
- **judge** — bind before run + verdict.
- **receipt** — Observation + PASS/FAIL/SKIPPED, no `proven_pure`.
- **plan.lock** — frozen `module_hashes` and `interface_contract_hash`.
- **content_hash** — declaration + body canon. `ArtifactRef` is not included.
- **Observation** — facts of a run. Observed ≠ Proven.
- **SKIPPED** — not enough facts to judge. Not PASS.
- **toolchain** — `python_version` + `canon_kind` + `canon` (`python.ast.v1`) + `worker_hash` + `runtime_hashes` next to the lock, not in identity.
- **source_hash** — SHA-256 of the exec target file, compared before import. Extra lock key in 0.2.x. Missing → SKIPPED.
- **supervisor** — the `acid-judge` binary: bind → worker → verdict. Not the body canon.
