# Integrity Coverage

Not a product tour. Each row is a real guard. `?` means we do not claim it.
Unknown is not safe — that is SKIPPED, not PASS.

This is coverage of **approved → executed**, not a list of 100 CVE classes.

| Attack | Detect | Block | Execute | Receipt | Guard |
| --- | ---: | ---: | ---: | ---: | --- |
| Body swap | ✓ | ✓ | ✗ | ✓ | `test_compute_amount_tamper` (`source_hash`) |
| Import-time side effect | ✓ | ✓ | ✗ | ✓ | `test_import_time` |
| Import-time via JSON blank | ✓ | ✓ | ✗ | ✓ | `test_json_blank_side_effect_blocked_before_load` |
| Import-time via PreToolUse hook | ✓ | ✓ | ✗ | ✓ | `test_hook_import_side_effect_does_not_run` |
| PreToolUse unknown tool | ✓ | ✓ | ✗ | — | `test_hook_unknown_tool_is_deny` |
| PreToolUse same-stem / stolen id | ✓ | ✓ | ✗ | — | `test_hook_same_stem_foreign_file_is_deny` |
| PreToolUse foreign repo / tamper | ✓ | ✓ | ✗ | — | `test_hook_foreign_repo_tamper_is_deny` (`ACID_REPO_ROOT`) |

| Static helper swap | ✓ | ✓ | ✗ | ✓ | `test_local_deps` / supervisor `test_rust_dep_seal` |
| Hasher / contour swap | ✓ | ✓ | ✗ | ✓ | `test_cli_judge_runtime_mismatch` / `cli_judge.py` + `action_driver.py` pin |
| Poisoned expected hash | ✓ | ✓ | ✗ | ✓ | same |
| `importlib.import_module` | ⚠ warn | ✗ | ✓ | ✓ | `test_dynamic_import_lock_warns` |
| `exec` / `eval` in AST | ⚠ warn | ✗ | ✓ | ✓ | same detector |
| `judge` without `--plan` | ✓ | SKIPPED | ✗ | ✓ | `test_cli` |
| Wrong CPython (distant) | ✓ | ✓ | ✗ | ✓ | `test_lock_toolchain` |
| `max_latency_ms` overrun | ✓ | ✓ | ran | ✓ | rust `latency_over_limit_fail` |
| `Policy.pure` disk write | ✗ | ✗ | ✓ | ✓ | declared_pure; not instrumented |
| Shell outside `judge` | ✗ | ✗ | ✓ | — | out of perimeter |
| Symlink retarget | ✓ | ✓ | ✗ | ✓ | `test_symlink` |
| Lazy import TOCTOU | ✓ | ✓ | ✗ | ✓ | `test_toctou` (locked hash, one read) |
| Concurrent same-named helpers | ✓ | ✓ | ✗ | ✓ | `test_concurrent_helpers` |
| ArtifactRef file swap before import | ✓ | ✓ | ✗ | ✓ | `test_artifact_source_hash_mismatch_does_not_import` |
| ArtifactRef entry swap before import | ✓ | ✓ | ✗ | ✓ | `test_artifact_body_hash_mismatch_does_not_import` |
| Replay poisoned runtime contour | ✓ | ✓ | ✗ | ✓ | `test_replay_poisoned_runtime_does_not_execute` |
| Replay swapped helper | ✓ | ✓ | ✗ | ✓ | `test_replay_modified_dependency_does_not_execute` |
| Undeclared helper after lock | ✓ | ✓ | ✗ | ✓ | `test_toctou` |
| Hostile `cwd/acid_engine` | ✓ | ✓ | ✗ | ✓ | supervisor `PYTHONPATH` trusted first |
| Action without a release tag | — | python-cli | — | — | `uses: ./` logs `path=python-cli`; no `@main` fetch |
| Action asset checksum mismatch | ✓ | python-cli | — | — | `sha256sum -c`; log `checksum mismatch`; do not fail open on the binary |
| `cli.py` help patch | ✗ tagged Action | supervisor | ✗ | ✓ | tagged path does not call argparse CLI |
| `cli.py` help patch | ✓ pip CLI | — | ✓ | ✓ | argparse is not in the pin |
| `cli_judge.py` / `cmd_judge` patch | ✓ pip CLI | — | ✗ | ✓ | PASS is `cli_judge.py` (in the pin) |



| Env mutation | ✗ | ✗ | ✓ | ✓ | not in identity |
| site-packages swap | ✗ | ✗ | ✓ | ✓ | supply chain, not this gate. argparse `cli.py` is not pin; `cli_judge.py` / worker are |
| Malicious *approved* body | — | — | ✓ | ✓ | identity, not correctness |

How to run the claimed rows:

```bash
pip install -e ".[dev]"
python -m pytest tests/integration/test_compute_amount_tamper.py tests/integration/test_local_deps.py tests/integration/test_cli.py tests/integration/test_cli_judge_pin.py -q
```

Manual copies: [ATTACK.md](../ATTACK.md). Trust model: [TRUST.md](../TRUST.md).
