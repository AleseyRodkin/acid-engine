"""ContractRegistry — библиотека атомов (уровень 4)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from acid_engine.level2.identity import ContractId
from acid_engine.level3.script.module import ScriptModule


class ContractRegistry:
    """
    Хранит ScriptModule проекта и список версий.
    Не журнал прогонов: регистрация — не исполнение.
    """
    def __init__(self) -> None:
        self._modules: dict[str, ScriptModule] = {}
        self._versions: dict[str, list[str]] = {}

    def register(self, module: ScriptModule) -> None:
        """Зарегистрировать модуль. Не создаёт RunRecord и не ставит success."""
        key = str(module.contract_id)
        self._modules[key] = module
        vers = str(module.version)
        known = self._versions.setdefault(key, [])
        if vers not in known:
            known.append(vers)

    def resolve(self, contract_id: ContractId) -> ScriptModule:
        """Получить актуальную реализацию модуля по идентификатору."""
        key = str(contract_id)
        if key not in self._modules:
            raise KeyError(f"Contract '{key}' not found in registry")
        return self._modules[key]

    def list_versions(self, contract_id: ContractId) -> list[str]:
        """Версии, с которыми модуль регистрировали. Не run_id."""
        return list(self._versions.get(str(contract_id), []))

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
