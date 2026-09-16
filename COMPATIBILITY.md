# Compatibility (0.2.x)

Public contract for an adopter who pins a 0.2 lock and CLI in their own CI.

- **Index:** `schema: acid.locks.v1`. Unknown keys are ignored.
- **Receipt:** `schema: acid.receipt.v1`. Extra keys ignored. `evidence.missing`
  is a list of facts that were not present (SKIPPED). Empty on PASS and FAIL.
  Optional `context.agent` / `context.repository` — attribution, not identity.
  Not a risk score. Not SLSA provenance.
- **CLI in 0.2.x:** `lock`, `judge`, `locks`, `diff`, `receipt` keep their names
  and required flags (`--script`, `--plan`, `--out`, `--index`).
- **Patch (0.2.n)** may add keys and warnings. It does not rename or remove keys
  that existed in 0.2.4.
- **Breaking** lock format or CLI → 0.3.0.
- **PyPI (0.2.15+):** `pip install acid-judge`. Import `acid_engine`. The
  distribution `acid-engine` on PyPI is a different product and stays that way.

Supervisor contour: `ACID_ENGINE_ROOT`, else the installed package
(`python -P -c "import acid_engine"`), else `cwd/acid_engine/` last.
User `cwd` is the project, not the front of `PYTHONPATH`.
`source_hash` is an extra lock key in 0.2.x. A 0.2.13 lock without it is
SKIPPED, not PASS. Re-take the lock.
`ArtifactRef.source_hash` is additive (default empty). Empty still loads;
a filled value is compared before import.
PreToolUse 0.2.20+: a tool that reached the hook and is not in the index is
deny. 0.2.19 allowed unknown. The settings matcher is unchanged.
