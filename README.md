# Acid Judge

Агент вызовет только залоченное тело; вердикт по наблюдению.

Fail-closed gate тела Python-tool. Не ОС разработки, не SaaS, не `proven_pure`.
Пакет **0.1.0**. Ядро MIT.

## Три команды

| Команда | Роль |
|---|---|
| `lock` | замок на тело |
| `judge` | bind до run + вердикт |
| `receipt` | `judge … --receipt FILE` — Observation + PASS/FAIL/SKIPPED, без `proven_pure` |

`locks --index` — сверка живого тела с замком в git. Не исполняет, не hosted.
`receipt --sign` / `receipt --verify` — Ed25519 на каноне receipt, локальный openssl. Не Sigstore.

```bash
PYTHONPATH=. python -m acid_engine lock --script FILE --out LOCK.json
PYTHONPATH=. python -m acid_engine judge --script FILE --plan LOCK.json --input '...'
PYTHONPATH=. python -m acid_engine locks --index locks/index.json
PYTHONPATH=. python -m acid_engine receipt --verify FILE --sig FILE.sig.json --pubkey ed25519.public.pem
```

`judge` = нынешний `run --script --plan`. Без `--plan` → SKIPPED, не PASS.

Витрина:

```bash
PYTHONPATH=. python -m acid_engine lock --help
PYTHONPATH=. python -m acid_engine judge --script examples/bones/n_plus_one.json --plan examples/bones/n_plus_one.plan.json --input '{"n": 3}' --receipt /tmp/bones.receipt.json
```

Коротко, почему не PASS: тело не то / не было исполнения / pure но effects / тип не совпал / замок не передан.

Закон рантайма: [METHOD.md](METHOD.md). Кости 0.1: [PLAN.md](PLAN.md). Очередь продукта: [COMMERCIAL.md](COMMERCIAL.md). Лицензия: [LICENSE](LICENSE).

## Проверки

```bash
PYTHONPATH=. python -m pytest tests -q --ignore=tests/property --ignore=tests/unit/test_async.py
PYTHONPATH=. python locks/ci_judge.py
cargo test --locked --manifest-path rust/acid-judge/Cargo.toml
```

CI: [.github/workflows/acid-judge.yml](.github/workflows/acid-judge.yml) судит [locks/index.json](locks/index.json). Job падает, если tool не PASS. Receipt — artifact. Без `plan` в индексе не судит.

Dev: `pip install -e ".[dev]"` — pytest, ruff, mypy.

```bash
ruff check acid_engine tests examples
mypy acid_engine
```

## Что держит gate

- Хеш = декларация + канон тела (`ast.unparse`, иначе байткод). `ArtifactRef` не identity.
- `plan.lock` до run. Несовпадение → FAIL, тело не запускается.
- Нет исполнения → не PASS. Мало фактов → SKIPPED. `bool ≠ int`.
- Worker не пишет PASS/FAIL. `judge_script` без plan+iface → SKIPPED (self-lock не вердикт). `lock --script` только снимает JSON.
- Бинарь `acid-judge` без `worker` не судит: SKIPPED. Observation без worker — не вердикт.

Пять tools: [examples/tools/](examples/tools/) (`clean_text`, `normalize_id`, `compute_amount`, `route_ticket`, `emit_forecast_card`) — в [locks/index.json](locks/index.json) вместе с bones.

Hook (один): [examples/hooks/pre_tool_use.py](examples/hooks/pre_tool_use.py) — Claude Code PreToolUse, только bind. Чужой хеш → deny. Pre ≠ PASS. MCP нет.

## Чего нет в 0.1

MCP hook, Sigstore-SaaS, hosted registry, markdown-спеки, WASM, JS-тело, STOL, ценники.
