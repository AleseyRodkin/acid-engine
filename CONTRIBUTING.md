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

PyPI: one distribution name. Trusted Publishing:

[pending Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
on the PyPI account:

- PyPI project name: `acid-judge`
- Owner: `AleseyRodkin`
- Repository: `acid-engine`
- Workflow: `pypi.yml`
- Environment: leave empty

After a GitHub rename, edit the publisher's repository field if it still says `acid-engine-2.0`.
Then tag `v0.2.n` (must match `pyproject.toml`) and let `.github/workflows/pypi.yml` upload `acid-judge` only.
Source `pyproject.toml` stays `name = "acid-judge"`. Do not publish this tree as `acid-engine`.
The archived data-contracts tree is `acid_engine_archive` (`acid-engine==0.2.0`).
Yank `acid-engine` 0.2.21 and 0.2.22 on PyPI if they are still live.