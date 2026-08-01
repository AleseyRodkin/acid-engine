"""
Шаблон ScriptModule.
Скопируй этот файл, измени IMPLEMENTATION и метаданные.
"""
from acid_engine.contracts.identity import ContractId, Version
from acid_engine.scripts.specification import Specification, Parameters, Policy
from acid_engine.scripts.module import ScriptModule

script = ScriptModule(
    contract_id=ContractId(namespace="user", name="my_script"),
    version=Version(0, 1, 0),
    specification=Specification(
        parameters=Parameters({}),
        policy=Policy(pure=True, max_latency_ms=100),
    ),
    input_type="int",
    output_type="int",
    implementation=lambda x: x * 2,  # <-- измени здесь
    name="my_script",
)