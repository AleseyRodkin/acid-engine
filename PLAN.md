# AcidEngine 0.1 — план костей

Бриф для сборщика. Закон — только [METHOD.md](METHOD.md).
ARCHITECTURE.md не план (хвост «ОС» до сужения 21.08).

**Дата:** 31.08.2026
**Репо:** https://github.com/AleseyRodkin/acid-engine-2.0
**HEAD старта:** `8e1b2a7`
**Python ≥ 3.11, 0 runtime-зависимостей**
**Старт тестов:** 165 passed

Очередь жёсткая. Сборщик начинает с фазы 1. Не с Rust, не с README, не с ARCHITECTURE.

```text
1 бланк → 2 ArtifactRef → 3 JSON-загрузчик → 4 тупая крышка →
5 фикстура bones → 6 вход судьи → 7 Rust (позже) → 8 JS/WASM/STOL никогда сейчас
```

## Форма продукта

Личный архитектурный эксперимент. Не коммерческий станок.
STOL (лаборатория) — чужой проект: не стенд, не фикстура, не пример.

Четыре кости + судья. Реализация и runtime — мясо, в каркас не входят.

| Кость | Роль |
|---|---|
| Contract | обещание: кто, вход, выход, правила |
| Container | снимок данных на порте |
| Script | один шаг: контейнер → контейнер + след |
| Graph | кто за кем (fan-in > 1 без merge запрещён) |
| Judge | отпечаток тела, замок до run, факт, вердикт |

Успех: нет пятой кости; тело не пишет закон; автор тела не патчит судью.

Не писать в README, пока не бежит: «каркас любого проекта», «любой язык», «судья на Rust», «ОС разработки».

## Закон (нельзя сломать)

Если этот бриф спорит с METHOD.md — прав METHOD. ИИ не арбитр. Observed ≠ Proven.

- Хеш `ScriptModule` / `AsyncScriptModule` = декларация + тело. Канон: AST, иначе байткод. Замыкания и defaults входят.
- Канон тела: `acid_engine/level2/implementation_canon.py`. Хеш: `canonical_serialize` + SHA-256 → `content_hash_of`.
- Нет исполнения → не PASS. Мало фактов → SKIPPED.
- `execute_plan` / `replay_run` сверяют хеш **до** run. Нет хешей в lock → SKIPPED. Несовпадение → FAIL, тело не запускать.
- `bool ≠ int`. Ядро не печатает stdout. Пустые effects ≠ proven pure. `pure=True` + эффекты → FAIL.
- CLI: load → resolve → execute. `run --script` через `execute_plan`. Markdown-спеки не парсятся.
- `replay_run` без `expected_output` → SKIPPED. `find_record` — lookup, не откат.

Тесты-стражи: `tests/unit/test_identity_hash.py`, `test_plan_lock_bind.py`, `test_purity_boundary.py`; `tests/architecture/test_invariants.py`.

## Фазы

| Ф | Суть | Готово |
|---|---|---|
| 0 | Форма: PLAN.md, CONSTITUTION. METHOD не переписывать | не повторять |
| 1 | `level2/blank.py` + `tests/unit/test_blank.py`. Identity без смены `_identity_dict` | хеш бланка = content_hash; 165 живы |
| 2a | ArtifactRef рядом; `artifact` опционально; хеш как сейчас | `49a7cb3`+ : `artifact.py`, хеш без новых ключей |
| 2b | Ссылка вместо fn. Нет языка python → не PASS. Битая ссылка → FAIL | resolve.py: python file+entry; unknown language FAIL; missing SKIPPED |
| 3 | JSON-почерк, CLI `.json`, `.md` отказ | blank_loader.py; JSON+py один хеш; max_latency_ms → float |
| 4 | `Pipeline.execute` через `execute_plan` | нет публичного PASS без lock |
| 5 | `examples/bones/` dict n:3→n:4 + .json + integration | без STOL |
| 6 | `judge.py` фасад → `execute_plan` | один вход |
| 7 | Rust только после стабильных 1–3 | тот же status на фикстурах |
| 8 | Не делать: STOL, JS-тело, WASM, JSON Schema, proven_pure, SaaS, markdown parser | запрет |

### Фаза 1 — детали

Файл `acid_engine/level2/blank.py`.
Функции: `script_identity_blank`, `container_blank`, `plan_blank`, `graph_blank`, `observation_blank`, `conformance_blank`, `parse_script_identity_blank`.

`script_identity_blank` = `_identity_dict` без `content_hash`.
Обёртка `{schema,kind,identity}` можно; schema/kind не входят в хеш.

Равенство: `content_hash_of(script_identity_blank(script)) == script.content_hash`

Нельзя: pydantic, JSON Schema, менять `ScriptModule.__init__`, менять состав `_identity_dict`, Rust, YAML, CLI, новые типы входа.

Ключ в lock (`_locked_hash_for`) не ломать.
`cmd_validate` не трогать в фазах 1–3.

Не начинать N+1, пока N не зелёная.

Проверка:

```text
PYTHONPATH=. python -m pytest tests -q --ignore=tests/property --ignore=tests/unit/test_async.py
```
