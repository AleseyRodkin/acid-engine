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
- **PyPI (0.2.15+):** `pip install acid-judge`. Import `acid_engine`. CLI `acid-judge`.
  `acid-engine==0.2.0` is the archived data-contracts product. 0.2.21–0.2.22 on
  that name are yanked. Do not install `acid-engine` for Acid Judge.

Supervisor contour: `ACID_ENGINE_ROOT`, else site-packages / sys.path
(the installed package, without importing it), else `cwd/acid_engine/` last.
User `cwd` is the project, not the front of `PYTHONPATH`.
`source_hash` is an extra lock key in 0.2.x. A 0.2.13 lock without it is
SKIPPED, not PASS. Re-take the lock.
`runtime_hashes` in 0.2.29 includes `acid_engine/action_driver.py` (8 keys).
A lock without that key FAILs the live pin. Re-take the lock on CPython 3.11.
`cli.py` is still not a pin key. Supervisor `dep:*` silence is FAIL, not SKIPPED.
Supervisor `bind()` FAILs if `dependency_hashes` is set but `dep:*` was cut
from `module_hashes`, or a `dep:` value is empty. Not a second hasher.

The Rust crate `acid-judge` (`rust/acid-judge`) is `publish = false` on
crates.io. Version in Cargo.toml tracks the Python release (0.2.32). GitHub
Release assets are the three supervisor binaries plus `<artifact>.sha256`,
not a crates.io crate. The supervisor binary exits 0 PASS / 1 FAIL / 2 input
error or SKIPPED. JSON body is unchanged. `action_driver.py` is not a CLI verb.
It is in `runtime_hashes`.

`ArtifactRef.source_hash` is required to exec (0.2.31). Empty does not load.
JSON blanks snapshot the file and fill the digest on the authoring path.
A filled value is compared before import.
PreToolUse 0.2.20+: a tool that reached the hook and is not in the index is
deny. 0.2.19 allowed unknown. The settings matcher is unchanged.
PreToolUse 0.2.28+: `ACID_REPO_ROOT` (else cwd) and `ACID_LOCKS_INDEX`
(else `$ACID_REPO_ROOT/locks/index.json`). The hook does not insert the
product tree on `sys.path`. Copy the script; install `acid-judge`.
The reusable fragment matcher is `YOUR_TOOL_ID`. Product ids are in
`examples/hooks/claude_settings.product.fragment.json`.

