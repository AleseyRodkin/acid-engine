# AcidEngine 0.1.0

Hard gate для Python-функции под контрактом.

Код пишет человек или ИИ. Арбитр — проверяемый контракт, не модель.
Система не имеет права утверждать больше, чем наблюдала.
`Observed ≠ Proven`: один чистый прогон не доказывает `pure`.

Это не операционная система разработки, не self-hosting и не замена Pydantic/Pandera.

## Что сейчас работает

- `ScriptModule`: CONSTRAINTS / INPUT / OUTPUT / IMPLEMENTATION
- `content_hash` покрывает декларацию **и тело реализации**
- `run` → Observed → структурная/операционная проверка → PASS / FAIL
- Walking skeleton: вход `3` → выход `4`
- Первый реальный пайплайн (слой A): `examples/commerce/order_amounts.py` — filter → scale сумм заказа, plan.lock, Observed, gate
- Второй: `examples/commerce/sku_normalize.py` — clean → dedupe SKU каталога
- `Pipeline(ScriptModule)` исполняет и проверяет
- Нет исполнения → не PASS (`InterfaceContract` в Pipeline, `LocalAdapter` → SKIPPED)

```bash
python -m acid_engine run
python -m acid_engine run --script path.py --input 3
python -m acid_engine validate contract.py echo hello
```

`run --script` грузит переменную `script` из `.py`.
`validate` принимает `.py` с переменной `contract`. Markdown-спеки не парсятся.

См. [METHOD.md](METHOD.md) — закон. Если правила нет в рантайме, его нет в METHOD и его нельзя писать сюда.

## Чего в 0.1 нет

Профили сборки (Library/CLI/SaaS/Embedded), DSL, AI-context, aggregator,
`validate spec.md`, формальная верификация, `proven_pure`.
