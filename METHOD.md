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

1. AST исходника, если исходник читается и парсится;
2. иначе байткод того, что реально исполняется.

Замыкания и defaults входят в хеш: они часть того, что бежит.
Разное тело → другой хеш. Подмена `x+1` на `x+100` при той же декларации
ломает `content_hash` и `plan.lock`.

## Наблюдение

После прогона есть Observed.
`Observed ≠ Proven`. Один чистый прогон не даёт `proven_pure`.
Пустые `effects_observed` ≠ доказательство чистоты.
ИИ не арбитр.

## Gate

Нет исполнения → не PASS.
`SKIPPED`, если фактов мало, чтобы судить.
Заглушка не может PASS: неисполненный `InterfaceContract` в `Pipeline`,
`LocalAdapter`-placeholder — даже на мусорном входе.

## CLI

`main()` / CLI не содержат бизнес-оркестрации сверх:
`load → resolve → execute` уже разрешённого контракта.

`run` — walking skeleton.
`run --script file.py` — грузит переменную `script` (`ScriptModule`) и исполняет.
`validate` принимает `.py` с переменной `contract`. Markdown-спеки не парсятся.


## Типы

`bool ≠ int`. `True`/`False` не проходят как `int`.

## Graph

Fan-in > 1 в Composite запрещён, пока нет merge-контракта.
Молча брать только `preds[0]` нельзя.

## Observation

Ядро не печатает в stdout. Лог observation — только opt-in через переданный logger.


## Pipeline

`Pipeline.execute` возвращает `PipelineResult`: `data`, `observation`, `conformance`.
Interface без исполнения → SKIPPED, `data=None`, `observation=None`.

## CLI input

`--input`: int, JSON (list/dict) или строка. Не только int.
