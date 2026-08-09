import pytest
from examples.atomic_storage.storage import AtomicStorage
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification


def make_module(name: str) -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("test", name),
        version=Version(1, 0, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=lambda x: x,
        name=name,
    )


def test_store_and_load():
    store = AtomicStorage()
    mod = make_module("m1")
    store.store(mod)
    loaded = store.load(ContractId("test", "m1"))
    assert loaded.contract_id == mod.contract_id
    assert loaded.name == "m1"


def test_versioning():
    store = AtomicStorage()
    mod_v1 = make_module("m2")
    store.store(mod_v1)
    # Сохраняем "вторую версию" (с тем же id, но другой хеш)
    mod_v2 = ScriptModule(
        contract_id=ContractId("test", "m2"),
        version=Version(2, 0, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=lambda x: x * 2,
        name="m2_v2",
    )
    store.store(mod_v2)
    versions = store.list_versions(ContractId("test", "m2"))
    assert len(versions) == 2
    # Загружаем последнюю версию
    latest = store.load(ContractId("test", "m2"))
    assert latest.name == "m2_v2"