# Contributing

Runtime law: [METHOD.md](METHOD.md). If the runtime does not enforce it, do not put it in README.

```bash
pip install -e ".[dev]"
python -m ruff check acid_engine tests examples research
python -m mypy --strict acid_engine
python -m pytest tests -q
cargo test --locked --manifest-path rust/acid-judge/Cargo.toml
```

Changing a file in `runtime_hashes` requires reshooting every `*.plan.json` and `locks/index.json`.
Do not add `proven_pure`. Do not make SKIPPED into PASS. Do not sandbox. Do not add a second agent harness.
Vulnerability reports: [SECURITY.md](SECURITY.md), not a public issue.
