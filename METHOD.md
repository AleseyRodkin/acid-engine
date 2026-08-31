# METHOD

Закон AcidEngine. Если правило не исполняется рантаймом — его нет в этом файле
и его нельзя писать в README.

Код пишет человек или ИИ. Арбитр — проверяемый контракт, не модель.
Система не имеет права утверждать больше, чем наблюдала.

## Сущности

```text
Contract ≠ Container ≠ Graph ≠ Implementation ≠ Runtime
Parameters ≠ Policy ≠ ImplementationRequirements
```

Контракт скрипта: `CONSTRAINTS` / `INPUT` / `OUTPUT` / `IMPLEMENTATION`.
Это разные поля, не один мешок.

## Identity

Хеш `ScriptModule` и `AsyncScriptModule` покрывает декларацию **и тело реализации**.

Канон тела (один):

1. AST исходника через `ast.unparse` (не `ast.dump`: поля узла растут с CPython);
2. иначе байткод того, что реально исполняется.

Замыкания и defaults входят в хеш: они часть того, что бежит.
Разное тело → другой хеш. Подмена `x+1` на `x+100` при той же декларации
ломает `content_hash` и `plan.lock`.
Канон тела один: callable. `ArtifactRef` — локатор, не identity.
Нет callable → `implementation` в identity = `{kind: missing}`.
После резолва (`materialize_script`) identity — канон тела fn.
Замок снимать после materialize. Dict ссылки в хеш не входит.

## Наблюдение

После прогона есть Observed.
`Observed ≠ Proven`. Один чистый прогон не даёт `proven_pure`.
Пустые `effects_observed` ≠ доказательство чистоты.
ИИ не арбитр.

## Gate

Нет исполнения → не PASS.
`SKIPPED`, если фактов мало, чтобы судить.
`obs.status != completed` → не PASS (`failed` → FAIL, `skipped` → SKIPPED).
Заглушка не может PASS: неисполненный `InterfaceContract` в `Pipeline`,
`LocalAdapter`-placeholder — даже на мусорном входе.

## CLI

`main()` / CLI не содержат бизнес-оркестрации сверх:
`load → resolve → execute` уже разрешённого контракта.

`run --script` — через `judge_script` → `execute_plan`.
`run --script file.py` — грузит переменную `script` (`ScriptModule`) и исполняет.
`validate` принимает `.py` с переменной `contract`. Markdown-спеки не парсятся.
`judge_script`: plan и iface только вместе, иначе SKIPPED. Без обоих — замок на загруженное тело (библиотека).
`run --script` без `--plan` → SKIPPED (self-lock не вердикт).
`judge` — алиас `run --script --plan`. Без `--script` не walking skeleton.
`--plan` — JSON замка (`lock --script`). Markdown-спеки не парсятся.

## Rust judge

Один вход: bind `plan.module_hashes` ↔ хеш тела, который worker identify вернул.
С `worker`: identify → bind → `python -m acid_engine.worker` run → verdict.
Несовпадение хеша → FAIL, тело не run.
Вердикт Rust: status, output_type, pure, latency. Semantic/schema/invariants —
только Python `check_conformance`. Это не два полных судьи на одном JSON.
Без `worker`: зеркало по готовому observation. Нет observation после bind → не PASS.
Worker не пишет PASS/FAIL. Автор тела не патчит судью.
Не runtime и не WASM. cargo ≥ 1.75, lockfile v3.



## Типы

`bool ≠ int`. `True`/`False` не проходят как `int`.

## Graph

Fan-in > 1 в Composite запрещён, пока нет merge-контракта.
Молча брать только `preds[0]` нельзя.

## Observation

Ядро не печатает в stdout. Лог observation — только opt-in через переданный logger.


## Blank

`container_blank` несёт `data`. Без data шаг из бланка не собрать.
`parse_container_blank` сверяет `content_hash` с data. Несовпадение — ошибка.


## Pipeline

`Pipeline.execute` возвращает `PipelineResult`: `data`, `observation`, `conformance`.
`Pipeline.execute` для ScriptModule идёт через `execute_plan` / `plan.lock`.
Interface без исполнения → SKIPPED, `data=None`, `observation=None`.

## CLI input

`--input`: int, JSON (list/dict) или строка. Не только int.

## History

`replay_from_record` возвращает `ConformanceResult`, не bool.
Факт выхода — `expected_output` или `record.output_data`. Несовпадение → FAIL.
`find_record` — только lookup по `run_id`. Отката состояния нет.

## Plan.lock

`execute_plan` / `replay_run` сверяют `script.content_hash` с `plan.module_hashes`
**до** исполнения. Несовпадение → FAIL, тело не запускается.
Нет хешей в lock → SKIPPED.
`interface_contract_hash` тоже сверяется.
`replay_run` без `expected_output` → SKIPPED.
`execute_plan` возвращает `PipelineResult` (data + observation + conformance).

## Effects / DataPlane

`EffectCollector` собирает `effects_observed` за прогон.
`DataPlane.store` / `record_effect` — факт.
`policy.pure=True` и непустые `effects_observed` → FAIL.
`InMemoryDataPlane` и `FileSystemDataPlane`. Пустые effects ≠ proven pure.

## Composite

`Composite.execute` возвращает `CompositeResult`: `data` + `observations` + `conformance`.
Нет `conformance.ok` — не PASS.
Внешний `plan`+`iface` — bind листьев к замку. Одно без другого — не исполнять.
Без plan — self-lock листа (не замена чужого замка).

## CLI run

`run --script` без `--plan` не PASS. С `--plan` — `judge_script` / замороженный lock.
Не обходит lock прямым `run_script`.
`lock --script` пишет JSON замка, это не вердикт.

## History

`replay_from_record` без `plan` → SKIPPED. С `plan` → `replay_run`.

