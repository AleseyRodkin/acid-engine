"""Изолированное хранилище атомов (AtomicStorage)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
from acid_engine.level4.registry import ContractRegistry
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level1.data_plane import InMemoryDataPlane, DataPlane


class AtomicStorage:
    """
    Постоянное хранилище ScriptModule с версионированием и поиском.
    Использует DataPlane для хранения данных (по умолчанию in-memory).
    """
    def __init__(self, data_plane: Optional[DataPlane] = None):
        self.registry = ContractRegistry()
        self.data_plane = data_plane or InMemoryDataPlane()
        self._index: Dict[str, List[str]] = {}  # contract_id -> list of hashes

    def store(self, module: ScriptModule) -> None:
        """Сохраняет модуль в хранилище и реестре."""
        key = str(module.contract_id)
        # Сохраняем модуль как JSON в DataPlane
        serialized = json.dumps(module.to_canonical_dict(), ensure_ascii=False)
        content_hash = module.content_hash
        self.data_plane.store(f"{key}:{content_hash}", serialized.encode("utf-8"))
        # Обновляем индекс версий
        if key not in self._index:
            self._index[key] = []
        self._index[key].append(content_hash)
        # Регистрируем в реестре
        self.registry.register(module)

    def load(self, contract_id: ContractId, version_hash: Optional[str] = None) -> ScriptModule:
        """Загружает модуль по идентификатору и (опционально) версии."""
        key = str(contract_id)
        if version_hash is None:
            # Последняя версия
            if key not in self._index or not self._index[key]:
                raise KeyError(f"No versions for {key}")
            version_hash = self._index[key][-1]
        data = self.data_plane.load(f"{key}:{version_hash}")
        # Восстанавливаем объект из словаря (упрощённо)
        d = json.loads(data.decode("utf-8"))
        # Создаём ScriptModule (implementation будет заглушкой)
        return ScriptModule(
            contract_id=contract_id,
            version=Version(*(d.get("version", "0.0.0").split("."))),
            specification=None,  # не восстанавливаем
            input_type=d.get("input_type", "any"),
            output_type=d.get("output_type", "any"),
            implementation=lambda x: x,
            name=d.get("name", "")
        )

    def list_versions(self, contract_id: ContractId) -> List[str]:
        """Возвращает список хешей всех версий модуля."""
        return self._index.get(str(contract_id), [])

    def search_by_hash(self, content_hash: str) -> Optional[ContractId]:
        """Ищет модуль по хешу содержимого."""
        for cid, hashes in self._index.items():
            if content_hash in hashes:
                ns, name = cid.split("/", 1)
                return ContractId(ns, name)
        return None