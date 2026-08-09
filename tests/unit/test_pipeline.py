import pytest
from acid_engine.level3.pipeline import Pipeline
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy

def test_pipeline_with_script_module():
    script = ScriptModule(
        contract_id=ContractId("test", "inc"),
        version=Version(1,0,0),
        specification=Specification(policy=Policy(max_latency_ms=100)),
        input_type="int",
        output_type="int",
        implementation=lambda x: x + 1,
        name="increment",
    )
    pipeline = Pipeline(script)
    result = pipeline.execute(5)
    assert result.ok, f"Expected PASS, got {result.message}"
    # Дополнительно проверим, что выходные данные были правильными (через observation не достать, но можно через run_script отдельно)
    # Здесь просто проверяем, что проверка прошла