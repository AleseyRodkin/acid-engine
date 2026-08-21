"""Demo script for AcidEngine."""
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level3.script.module import ScriptModule

script = ScriptModule(
    contract_id=ContractId(namespace="demo", name="my_script"),
    version=Version(0, 1, 0),
    specification=Specification(
        policy=Policy(pure=True, max_latency_ms=100),
    ),
    input_type="int",
    output_type="int",
    implementation=lambda x: x + 1,
    name="demo_script",
)
