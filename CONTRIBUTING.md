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

PyPI: the distribution is `acid-judge`, not `acid-engine`. First publish needs a
[pending Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
on the PyPI account that already owns `acid-engine`:

- PyPI project name: `acid-judge`
- Owner: `AleseyRodkin`
- Repository: `acid-engine-2.0`
- Workflow: `pypi.yml`
- Environment: leave empty

Then tag `v0.2.n` (must match `pyproject.toml`) and let `.github/workflows/pypi.yml` upload.
Do not upload this tree to `pypi.org/project/acid-engine`.
