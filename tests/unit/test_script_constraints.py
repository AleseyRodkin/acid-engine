import pytest
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.scripts.specification import (
    Specification, ImplementationRequirements,
)
from acid_engine.scripts.module import ScriptModule
from acid_engine.scripts.validation import validate_implementation_requirements


def my_func(x):
    return x


def test_no_requirements():
    script = ScriptModule(
        contract_id=ContractId("test", "ok"),
        version=Version(1,0,0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=my_func,
    )
    assert validate_implementation_requirements(script) == []

def test_required_methods_missing():
    script = ScriptModule(
        contract_id=ContractId("test", "bad"),
        version=Version(1,0,0),
        specification=Specification(
            implementation_requirements=ImplementationRequirements(
                required_methods=("transform",)
            )
        ),
        input_type="int",
        output_type="int",
        implementation=my_func,
    )
    errors = validate_implementation_requirements(script)
    assert len(errors) == 1
    assert "transform" in errors[0]

def test_required_methods_present():
    class Impl:
        def transform(self, x):
            return x
        def __call__(self, x):
            return self.transform(x)
    impl = Impl()
    script = ScriptModule(
        contract_id=ContractId("test", "good"),
        version=Version(1,0,0),
        specification=Specification(
            implementation_requirements=ImplementationRequirements(
                required_methods=("transform",)
            )
        ),
        input_type="int",
        output_type="int",
        implementation=impl,   # передаём сам callable объект
    )
    assert validate_implementation_requirements(script) == []