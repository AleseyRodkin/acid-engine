# AcidEngine 0.1.0

Жёсткий gate для шага под контрактом: тело бежит, судья сравнивает факт с обещанием.

Код пишет человек или ИИ. Арбитр — проверяемый контракт, не модель.
Система не имеет права утверждать больше, чем наблюдала.
`Observed ≠ Proven`.

Это не операционная система разработки, не SaaS, не self-hosting
и не замена Pydantic/Pandera. Версия пакета — **0.1.0** (не «v3»).

Закон, который исполняет рантайм: [METHOD.md](METHOD.md).
Очередь костей: [PLAN.md](PLAN.md). Лицензия: [LICENSE](LICENSE) (MIT).

## Что есть

Четыре кости + судья: Contract, Container, Script, Graph; Judge.

- Хеш `ScriptModule` покрывает декларацию **и тело** (AST, иначе байткод).
- `judge_script` → `execute_plan` / `plan.lock` **до** run. Нет исполнения → не PASS.
- Мало фактов → SKIPPED. Подмена тела → FAIL, fn не вызывается.
- `bool ≠ int`. `pure=True` + эффекты → FAIL. Пустые effects ≠ proven pure.
- CLI: `.py` (переменная `script`) или `.json` blank. Markdown не парсится.
  `run --script` без `--plan` → SKIPPED. `lock --script` пишет JSON замка.
- Фикстура: `examples/bones/` `{n: 3}` → `{n: 4}`.
- Пайплайны: `examples/commerce/order_amounts.py`, `sku_normalize.py`.
- Rust `rust/acid-judge`: с `worker` — bind → `python -m acid_engine.worker` → verdict.
  Без `worker` — зеркало по observation. cargo ≥ 1.75, lockfile v3.

Python ≥ 3.11, **runtime-зависимостей нет**.

```bash
PYTHONPATH=. python -m pytest tests -q --ignore=tests/property
PYTHONPATH=. python -m acid_engine run --script examples/bones/n_plus_one.json --plan examples/bones/n_plus_one.plan.json --input '{"n": 3}'
cargo test --manifest-path rust/acid-judge/Cargo.toml
```

Dev: `pip install -e ".[dev]"` — pytest, ruff, mypy.

```bash
ruff check acid_engine tests examples
mypy acid_engine
```

## Чего в 0.1 нет

Профили Library/CLI/SaaS/Embedded, DSL, AI-context, aggregator,
`validate spec.md`, формальная верификация, `proven_pure`, WASM, JS-тело, STOL.
