"""ContractRegistry — библиотека атомов (уровень 4)."""
from __future__ import annotations

from typing import Dict, List, Optional
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level4.history import HistoryStore, RunRecord
from acid_engine.level2.loader import PythonLoader
from pathlib import Path


class ContractRegistry:
    """
    Хранит все контракты проекта с историей версий и разрешением ссылок.
    """
    def __init__(self):
        self._modules: Dict[str, ScriptModule] = {}          # key = contract_id
        self._history: Dict[str, HistoryStore] = {}          # key = contract_id
        self._loader = PythonLoader()

    def register(self, module: ScriptModule) -> None:
        """Зарегистрировать модуль в реестре."""
        key = str(module.contract_id)
        if key not in self._history:
            self._history[key] = HistoryStore()
        # Добавляем запись в историю (условно, без реального выполнения)
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

    def list_versions(self, contract_id: ContractId) -> List[str]:
        """Вернуть список известных версий модуля."""
        key = str(contract_id)
        if key in self._history:
            return [r.run_id for r in self._history[key].records]
        return []

    def load_from_file(self, path: str | Path) -> ScriptModule:
        """Загрузить модуль из Python-файла и сразу зарегистрировать."""
        module = self._loader.load(path)
        self.register(module)
        return module