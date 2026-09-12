# Acid Judge

ИИ может написать или изменить tool. Acid Judge не обязан ему верить. Он проверяет, что будет запущен именно тот код, который был одобрен, и отдельно сверяет наблюдение с контрактом. Нет фактов — SKIPPED, не PASS.

An agent can write or change a tool. Acid Judge does not have to believe it. It checks that the approved body is what will run, then checks the observation against the contract. Not enough facts → SKIPPED, not PASS.

Trust continuity: approved → unchanged → executed → observed → verified. Not a checksum feature. The trust layer sits between the agent and the Python tool it is about to run.

Замок ловит подмену файла tool между `lock` и `judge`; не ловит shell и не ловит файлы вне `runtime_hashes`.

Fail-closed gate of a locked Python-tool body. Catches a file swap between `lock` and `judge`. Does not catch a shell, does not sandbox the body after PASS, is not a development OS.

Fail-closed gate тела Python-tool. Не ОС разработки, не SaaS, не `proven_pure`, не песочница.
Пакет **0.2.4**. Ядро MIT. Бинари supervisor: GitHub Releases (`linux` / `windows` / `macos`), без локального `cargo`.

Not an MCP gateway. Gateways watch poisoned *tool descriptions* on the network. Acid Judge checks *file bytes* of a locally approved Python tool (and the judge contour) right before the call. Complementary layer, not a substitute. Reproduce: [ATTACK.md](ATTACK.md).

Закон рантайма: [METHOD.md](METHOD.md).

## Что защищает и что нет

Защищает от подмены файла tool между `lock` и вызовом, если hook или CI сверяют хеш.
Не защищает от того, что делает само тело после PASS: нет изоляции fs/net/process.
Не защищает обход через `bash` / любой shell вне `judge`.
`pure=True` ловит только эффекты, которые runtime занёс в `effects_observed`.
Замок — отпечаток в конкретном toolchain. В JSON замка рядом с identity (не в хеше) пишутся `python_version`, `canon_kind`, `canon` (`python.ast.v1`), `worker_hash` и `runtime_hashes`. Смена CPython может потребовать пересъёма `plan.json`.
Supervisor сверяет SHA-256 контура (`worker.py`, `cli.py`, `python_runtime.py`, `runner.py`, `resolve.py`, `implementation_canon.py`) до identify. Нет пина — SKIPPED. Несовпадение — FAIL. `locks --index` и CLI `judge --plan` без пина — FAIL. `judge_script` без `toolchain` — SKIPPED. Неполный пин — FAIL. `judge_script_from_lock` читает пины из JSON замка.

## Три команды

| Команда | Роль |
|---|---|
| `lock` | замок на тело |
| `judge` | bind до run + вердикт |
| `receipt` | `judge … --receipt FILE` — Observation + PASS/FAIL/SKIPPED, без `proven_pure` |

`locks --index` — сверка живого тела с замком в git. Не исполняет, не hosted.
`diff --script --plan` — таблица approved vs live. Не исполняет, не PASS.
`receipt --sign` / `receipt --verify` — Ed25519 на каноне receipt, локальный openssl. Не Sigstore.

Продукт — Acid Judge. Import остаётся `acid_engine`. CLI — `acid-judge`. Репозиторий — `acid-engine-2.0`. На PyPI не публикуем: имя `acid-engine` уже занято чужим пакетом.

```bash
pip install "acid-engine @ git+https://github.com/AleseyRodkin/acid-engine-2.0.git"
acid-judge lock --script FILE --out LOCK.json
acid-judge judge --script FILE --plan LOCK.json --input '...'
acid-judge locks --index locks/index.json
acid-judge diff --script FILE --plan LOCK.json
acid-judge receipt --verify FILE --sig FILE.sig.json --pubkey ed25519.public.pem
```

`python -m acid_engine` — тот же CLI. `PYTHONPATH=.` не нужен после `pip install`.

Чужой репозиторий:

```yaml
- uses: AleseyRodkin/acid-engine-2.0@v0.2.4
  with:
    index: locks/index.json
    judge: true   # optional: execute + receipt. Default is bind only.
```

Без `judge: true` — только bind, тело не запускается. С флагом — `lock → judge → receipt`. Не песочница.
Чужой CI: [acid-judge-smoke](https://github.com/AleseyRodkin/acid-judge-smoke) — один tool, job `tamper` должен FAIL.

`judge` без `--plan` → SKIPPED, не PASS. Скрытый `run` ещё вызывается, в `--help` его нет.

Витрина:

```bash
acid-judge lock --help
acid-judge judge --script examples/bones/n_plus_one.json --plan examples/bones/n_plus_one.plan.json --input '{"n": 3}' --receipt /tmp/bones.receipt.json
acid-judge judge --script examples/bones/n_plus_one.json --input '{"n": 3}'
```

Коротко, почему не PASS: тело не то / не было исполнения / pure но effects / тип не совпал / замок не передан.

Лицензия: [LICENSE](LICENSE).

## Supervisor, не второй канон

Бинарь `acid-judge` — supervisor: identify → bind → run worker → verdict.
Хеш тела считает только Python canon. Без worker — SKIPPED, не PASS. Observation без worker — не вердикт.
Linux: [Releases](https://github.com/AleseyRodkin/acid-engine-2.0/releases). Windows/macOS собирает workflow `release-bins`.

## Проверки

```bash
pip install -e ".[dev]"
python -m pytest tests -q
python locks/ci_judge.py
cargo test --locked --manifest-path rust/acid-judge/Cargo.toml
```

CI: [.github/workflows/acid-judge.yml](.github/workflows/acid-judge.yml) — pytest (3.11/3.12), `locks/index.json`, cargo. Job падает, если tool не PASS. Receipt — artifact. Без `plan` в индексе не судит.

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
- Бинарь `acid-judge` без `worker` не судит: SKIPPED.

Пять tools: [examples/tools/](examples/tools/) (`clean_text`, `normalize_id`, `compute_amount`, `route_ticket`, `emit_forecast_card`) — в [locks/index.json](locks/index.json) вместе с bones.

Hook (один): [examples/hooks/pre_tool_use.py](examples/hooks/pre_tool_use.py) — Claude Code PreToolUse, только bind. Чужой хеш → deny. Pre ≠ PASS. MCP нет.

## Чего нет в 0.2

Песочница, MCP hook, Sigstore-SaaS, hosted registry, markdown-спеки, WASM, JS-тело, STOL, ценники, второй канон хеша на Rust.
