import pytest
import tempfile
from pathlib import Path
from acid_engine.level4.registry import ContractRegistry
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification


def make_script(name: str) -> ScriptModule:
    return ScriptModule(
        contract_id=ContractId("test", name),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=lambda x: x,
        name=name,
    )


def test_register_and_resolve():
    reg = ContractRegistry()
    mod = make_script("m1")
    reg.register(mod)
    resolved = reg.resolve(ContractId("test", "m1"))
    assert resolved is mod
    assert "reg_1.0.0" in reg.list_versions(ContractId("test", "m1"))


def test_resolve_unknown():
    reg = ContractRegistry()
    with pytest.raises(KeyError):
        reg.resolve(ContractId("test", "missing"))


def test_load_from_file():
    code = """from acid_engine.level3.script.module import ScriptModule
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification

contract = ScriptModule(
    contract_id=ContractId("tmp", "test"),
    version=Version(1,0,0),
    specification=Specification(),
    input_type="int",
    output_type="int",
    implementation=lambda x: x,
    name="tmp",
)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        reg = ContractRegistry()
        mod = reg.load_from_file(tmp_path)
        assert mod.contract_id.name == "test"
        # Проверяем, что зарегистрирован
        assert reg.resolve(ContractId("tmp", "test")) is mod
    finally:
        Path(tmp_path).unlink()