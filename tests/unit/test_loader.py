import pytest
import tempfile
from pathlib import Path
from acid_engine.contracts.loader import DictLoader, PythonLoader, load_contract
from acid_engine.interface.contract import InterfaceContract
from acid_engine.contracts.identity import ContractId, Version


def test_dict_loader():
    iface = InterfaceContract(
        contract_id=ContractId("test", "iface"),
        version=Version(1,0,0),
        inputs={}, outputs={}, constraints={},
    )
    loader = DictLoader({"my_contract": iface})
    assert loader.can_load("my_contract")
    loaded = loader.load("my_contract")
    assert loaded.content_hash == iface.content_hash

def test_python_loader():
    # Создаём временный .py файл с переменной contract
    code = '''from acid_engine.interface.contract import InterfaceContract
from acid_engine.contracts.identity import ContractId, Version
contract = InterfaceContract(
    contract_id=ContractId("tmp", "test"),
    version=Version(1,0,0),
    inputs={"x":"int"}, outputs={"y":"int"}, constraints={},
)
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        loader = PythonLoader()
        assert loader.can_load(tmp_path)
        contract = loader.load(tmp_path)
        assert contract.inputs == {"x": "int"}
    finally:
        Path(tmp_path).unlink()

def test_load_contract_fallback():
    # без загрузчиков — должен упасть на несуществующем файле
    with pytest.raises(ValueError):
        load_contract("/nonexistent/file.py", loaders=[])