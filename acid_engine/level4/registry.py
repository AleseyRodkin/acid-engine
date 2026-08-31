"""ContractRegistry — библиотека атомов (уровень 4)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from acid_engine.level2.identity import ContractId
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level4.history import HistoryStore, RunRecord


class ContractRegistry:
    """
    Хранит все контракты проекта с историей версий и разрешением ссылок.
    """
    def __init__(self) -> None:
        self._modules: dict[str, ScriptModule] = {}          # key = contract_id
        self._history: dict[str, HistoryStore] = {}          # key = contract_id

    def register(self, module: ScriptModule) -> None:
        """Зарегистрировать модуль в реестре."""
        key = str(module.contract_id)
        if key not in self._history:
            self._history[key] = HistoryStore()
        # Регистрация — не прогон. observation нет, success не из факта исполнения.
        record = RunRecord(
            run_id=f"reg_{module.version}",
            plan_hash=module.content_hash,
            timestamp=0,
            input_data=None,
            output_data=None,
            observation=None,
            success=True,
            note="registered"
        )
        self._history[key].add(record)
        self._modules[key] = module

    def resolve(self, contract_id: ContractId) -> ScriptModule:
        """Получить актуальную реализацию модуля по идентификатору."""
        key = str(contract_id)
        if key not in self._modules:
            raise KeyError(f"Contract '{key}' not found in registry")
        return self._modules[key]

    def list_versions(self, contract_id: ContractId) -> list[str]:
        """Вернуть список известных версий модуля."""
        key = str(contract_id)
        if key in self._history:
            return [r.run_id for r in self._history[key].records]
        return []

    def load_from_file(self, path: str | Path) -> ScriptModule:
        """Загрузить ScriptModule из .py (`script` или `contract`) и зарегистрировать."""
        source = Path(path)
        spec = importlib.util.spec_from_file_location(
            f"acid_registry_{source.stem}_{id(source)}", str(source)
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {source}")
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        obj = None
        if hasattr(loaded, "script"):
            obj = loaded.script
        elif hasattr(loaded, "contract"):
            obj = loaded.contract
        else:
            raise ValueError(f"{source} does not define 'script' or 'contract'")
        if not isinstance(obj, ScriptModule):
            raise TypeError(f"{source}: expected ScriptModule, got {type(obj)!r}")
        self.register(obj)
        return obj
