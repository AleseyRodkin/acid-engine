"""Abstract contract loader interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from acid_engine.level3.interface.contract import InterfaceContract


class ContractLoader(ABC):
    """Base class for loading InterfaceContract from any source."""

    @abstractmethod
    def can_load(self, source: str | Path) -> bool:
        """Whether this loader can handle the source."""
        ...

    @abstractmethod
    def load(self, source: str | Path) -> InterfaceContract:
        """Load InterfaceContract from the source."""
        ...


class DictLoader(ContractLoader):
    """Loader from a ready dict (tests and inline definitions)."""

    def __init__(self, contracts: dict[str, InterfaceContract]):
        self._contracts = contracts

    def can_load(self, source: str | Path) -> bool:
        return str(source) in self._contracts

    def load(self, source: str | Path) -> InterfaceContract:
        key = str(source)
        if key not in self._contracts:
            raise KeyError(f"Contract '{key}' not found in DictLoader")
        return self._contracts[key]


class PythonLoader(ContractLoader):
    """Load InterfaceContract from a Python module (expects a `contract` variable)."""

    def can_load(self, source: str | Path) -> bool:
        path = Path(source)
        return path.suffix == ".py" and path.exists()

    def load(self, source: str | Path) -> InterfaceContract:
        import importlib.util
        spec = importlib.util.spec_from_file_location("contract_module", str(source))
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {source}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "contract"):
            raise ValueError(f"Module {source} does not define 'contract'")
        obj = module.contract
        if not isinstance(obj, InterfaceContract):
            raise TypeError(
                f"{source}: 'contract' is {type(obj)!r}, expected InterfaceContract"
            )
        return obj


def load_contract(source: str | Path, loaders: list[ContractLoader] | None = None) -> InterfaceContract:
    """
    Universal load: try every passed loader.
    If loaders is omitted, use PythonLoader only.
    """
    if loaders is None:
        loaders = [PythonLoader()]
    for loader in loaders:
        if loader.can_load(source):
            return loader.load(source)
    raise ValueError(f"No loader can handle source: {source}")