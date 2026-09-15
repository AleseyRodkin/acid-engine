# Compatibility (0.2.x)

Public contract for an adopter who pins a 0.2 lock and CLI in their own CI.

- **Index:** `schema: acid.locks.v1`. Unknown keys are ignored.
- **Tool lock JSON:** extra keys are ignored. The trust anchor is `module_hashes`
  (body + static local `dep:` files). `interface_contract_hash` is derived, not
  a second gate.
- **CLI in 0.2.x:** `lock`, `judge`, `locks`, `diff`, `receipt` keep their names
  and required flags (`--script`, `--plan`, `--out`, `--index`).
- **Patch (0.2.n)** may add keys and warnings. It does not rename or remove keys
  that existed in 0.2.4.
- **Breaking** lock format or CLI → 0.3.0.

Supervisor contour: checkout `acid_engine/`, else `ACID_ENGINE_ROOT`, else the
installed package (`python -c "import acid_engine"`). User `cwd` is the project,
not the package tree.
