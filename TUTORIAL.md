# AcidEngine Tutorial

В этом руководстве вы шаг за шагом освоите AcidEngine — проверяемый контрактный контур вокруг Python-функции (версия 0.1).

## 1. Установка

```bash
cd acid-engine-2.0
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2. Первый контракт: ScriptModule

Создайте файл `my_script.py`:

```python
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy

script = ScriptModule(
    contract_id=ContractId("demo", "increment"),
    version=Version(1, 0, 0),
    specification=Specification(
        policy=Policy(
            pure=True,
            max_latency_ms=100
        )
    ),
    input_type="int",
    output_type="int",
    implementation=lambda x: x + 1,
    name="increment",
)
```

Запустите его через CLI:

```bash
python -m acid_engine run --script my_script.py --input 5
```

Вывод покажет `PASS` и результат `6`.

## 3. Семантические предикаты

Добавим проверку, что результат равен `6`.

Измените `my_script.py`, добавив `semantic_rules` в контракт:

```python
# ... (предыдущий код)

# Но CLI run пока не поддерживает семантические правила напрямую,
# поэтому используем Python API:

import time

from acid_engine.level3.script.python_runtime import run_script
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level2.conformance import check_conformance

# Выполнение
in_port = PortRef("demo", "input", "value")
snap = ContainerSnapshot.create(
    in_port,
    script.contract_id,
    script.content_hash,
    5
)

out_snap, obs, _, _ = run_script(script, snap)

# Проверка с equals
result = check_conformance(
    required_output_type="int",
    provided_data=out_snap.data,
    obs=obs,
    policy=script.specification.policy,
    semantic_rules={"equals": 6}
)

print(result.message)  # PASS
```

## 4. Композитный модуль и граф

Создайте два скрипта: `double.py` и `add_ten.py`, затем объедините их в граф.

### `double.py`

```python
script = ScriptModule(
    contract_id=ContractId("demo", "double"),
    version=Version(1, 0, 0),
    specification=Specification(
        policy=Policy(pure=True)
    ),
    input_type="int",
    output_type="int",
    implementation=lambda x: x * 2,
    name="double",
)
```

### `add_ten.py`

```python
script = ScriptModule(
    contract_id=ContractId("demo", "add_ten"),
    version=Version(1, 0, 0),
    specification=Specification(
        policy=Policy(pure=True)
    ),
    input_type="int",
    output_type="int",
    implementation=lambda x: x + 10,
    name="add_ten",
)
```

Постройте граф и выполните:

```python
from acid_engine.level3.module.leaf import LeafModule
from acid_engine.level3.module.composite import CompositeModule
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.script.python_runtime import run_script
from acid_engine.level2.conformance import check_conformance
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level3.script.module import ScriptModule

# Загружаем скрипты.
# В реальности это может выполняться через PythonLoader.
script_double = ScriptModule(
    ContractId("d", "d"),
    Version(1, 0, 0),
    Specification(),
    "int",
    "int",
    lambda x: x * 2
)

script_add = ScriptModule(
    ContractId("a", "a"),
    Version(1, 0, 0),
    Specification(),
    "int",
    "int",
    lambda x: x + 10
)

leaf_double = LeafModule("double", script_double)
leaf_add = LeafModule("add_ten", script_add)

g = DependencyGraph()
g.add_node("double")
g.add_node("add_ten")
g.add_edge("double", "add_ten")

composite = CompositeModule(
    module_id="pipeline",
    graph=g,
    modules={
        "double": leaf_double,
        "add_ten": leaf_add
    },
    contract_id=ContractId("demo", "pipeline"),
    version=Version(1, 0, 0),
    input_node="double",
    output_node="add_ten",
)

result = composite.execute(3)

print(result)  # 3 * 2 + 10 = 16
```

## 5. Использование CLI

AcidEngine предоставляет следующие команды.

### `init`

Пишет черновик markdown и опционально шаблон `.py` со `script`.
Markdown **не парсится** как контракт.

```bash
python -m acid_engine init --script my_script.py
```

### `run`

Выполнить скрипт или walking skeleton:

```bash
python -m acid_engine run \
    --script my_script.py \
    --input 10
```

### `validate`

Проверить внешнюю команду по контракту.

На текущем этапе поддерживаются Python-контракты, см. раздел `ExternalRunner`.

## 6. Внешний раннер

Запустите произвольную внешнюю команду и проверьте её результат:

```python
from acid_engine.level3.script.external_runner import run_external
from acid_engine.level2.identity import ContractId
from acid_engine.level2.specification import Policy
from acid_engine.level2.conformance import check_conformance

cid = ContractId("demo", "echo_test")

out_snap, obs, _, _ = run_external(
    command=["echo", "hello"],
    contract_id=cid,
    contract_hash="hash",
)

result = check_conformance(
    required_output_type="dict",
    provided_data=out_snap.data,
    obs=obs,
    policy=Policy(),
    semantic_rules={"contains": "hello"}
)

print(result.message)
```

## Заключение

В 0.1 есть: ScriptModule, исполнение, observation, проверка типа и latency,
линейный композит, CLI `run` / `run --script` / `validate` для `.py`.

Нет: self-hosting как продукта, AI-context, профилей сборки, парсера markdown-спек.
Заглушка не PASS. ИИ не арбитр. Закон — [METHOD.md](METHOD.md).
