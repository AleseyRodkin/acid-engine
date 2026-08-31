# Tutorial

Это не закон. Актуальный контур — [README.md](README.md). METHOD не переписывать по этому файлу.

Демо: залочить тело, прогнать `judge`, подменить формулу, увидеть FAIL и receipt.

## 1. Bones с `--plan`

Из корня репозитория:

```bash
PYTHONPATH=. python -m acid_engine judge \
  --script examples/bones/n_plus_one.json \
  --plan examples/bones/n_plus_one.plan.json \
  --input '{"n": 3}' \
  --receipt /tmp/bones.receipt.json
```

Код 0, PASS, `{n: 4}`. Receipt без `proven_pure`.

Без `--plan` это не вердикт:

```bash
PYTHONPATH=. python -m acid_engine judge \
  --script examples/bones/n_plus_one.json \
  --input '{"n": 3}'
```

Код ≠ 0, SKIPPED. Self-lock не PASS.

## 2. Lock `compute_amount`

Формула: `cents * qty`. Вход `{"cents": 1999, "qty": 2}` → `{"cents": 3998}`.

```bash
PYTHONPATH=. python -m acid_engine lock \
  --script examples/tools/compute_amount.py \
  --out examples/tools/compute_amount.plan.json
```

`lock` пишет JSON замка, не ставит PASS.

Честный прогон:

```bash
PYTHONPATH=. python -m acid_engine judge \
  --script examples/tools/compute_amount.py \
  --plan examples/tools/compute_amount.plan.json \
  --input '{"cents": 1999, "qty": 2}' \
  --receipt /tmp/amount-ok.receipt.json
```

PASS, `{"cents": 3998}`.

## 3. Подмена тела

В `examples/tools/compute_amount.py` заменить `cents * qty` на `cents * qty + 1`. JSON и `plan.json` не трогать.

```bash
PYTHONPATH=. python -m acid_engine judge \
  --script examples/tools/compute_amount.py \
  --plan examples/tools/compute_amount.plan.json \
  --input '{"cents": 1999, "qty": 2}' \
  --receipt /tmp/amount-bad.receipt.json
```

FAIL `module_hash`. Тело не исполняется. В receipt статус FAIL, поле `property`: `module_hash`. Не переснимать plan под новое тело — это уже другой замок.

Вернуть формулу `cents * qty`. Сломанное тело не коммитить.

## Чего здесь нет

Граф, `run` без `--plan` как успех, `judge_script` / Pipeline / Composite без пары plan+iface, semantic через ручной `run_script`, уровни 0–4.
