"""Execution Profiles — универсальные интерфейсы упаковки проекта."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level4.registry import ContractRegistry


class ExecutionProfile(ABC):
    """Базовый класс для профилей сборки артефактов."""

    @abstractmethod
    def build(self, project: InterfaceContract, registry: Optional[ContractRegistry] = None) -> Any:
        """Создаёт артефакт из проекта и реестра модулей."""
        ...


class LibraryProfile(ExecutionProfile):
    """Собирает проект как Python-библиотеку."""
    def build(self, project: InterfaceContract, registry: Optional[ContractRegistry] = None) -> str:
        return f"Library artifact: {project.contract_id} (v{project.version})"


class CLIProfile(ExecutionProfile):
    """Собирает проект как консольную команду."""
    def build(self, project: InterfaceContract, registry: Optional[ContractRegistry] = None) -> str:
        return f"CLI artifact: {project.contract_id}"


class DesktopProfile(ExecutionProfile):
    """Собирает проект как десктопное приложение."""
    def build(self, project: InterfaceContract, registry: Optional[ContractRegistry] = None) -> str:
        return f"Desktop artifact: {project.contract_id}"


class ServiceProfile(ExecutionProfile):
    """Собирает проект как микросервис (Docker-образ)."""
    def build(self, project: InterfaceContract, registry: Optional[ContractRegistry] = None) -> str:
        return f"Service artifact: {project.contract_id}"


class SaaSProfile(ExecutionProfile):
    """Разворачивает проект как облачный сервис."""
    def build(self, project: InterfaceContract, registry: Optional[ContractRegistry] = None) -> str:
        return f"SaaS artifact: {project.contract_id}"


class EmbeddedProfile(ExecutionProfile):
    """Собирает проект для встраиваемых устройств."""
    def build(self, project: InterfaceContract, registry: Optional[ContractRegistry] = None) -> str:
        return f"Embedded artifact: {project.contract_id}"