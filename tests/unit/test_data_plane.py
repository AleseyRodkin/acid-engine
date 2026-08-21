import tempfile
from pathlib import Path

from acid_engine.level1.data_plane import InMemoryDataPlane, FileSystemDataPlane
from acid_engine.level1.effects import EffectCollector, record_effect
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification, Policy
from acid_engine.level2.conformance import check_conformance, ConformanceStatus
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.python_runtime import run_script
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot


def test_inmemory_store_records_effect():
    plane = InMemoryDataPlane()
    with EffectCollector() as c:
        plane.store("k", b"v")
    assert plane.load("k") == b"v"
    assert any(e.startswith("dataplane.store:") for e in c.effects)


def test_filesystem_dataplane_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        plane = FileSystemDataPlane(tmp)
        plane.store("order:1", b'{"n":1}')
        assert plane.exists("order:1")
        assert plane.load("order:1") == b'{"n":1}'
        # reopen
        plane2 = FileSystemDataPlane(tmp)
        assert plane2.load("order:1") == b'{"n":1}'


def test_pure_plus_effects_is_fail():
    plane = InMemoryDataPlane()

    def writes(x):
        plane.store("side", str(x).encode())
        return x + 1

    script = ScriptModule(
        contract_id=ContractId("t", "fx"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(pure=True, max_latency_ms=500)),
        input_type="int",
        output_type="int",
        implementation=writes,
        name="fx",
    )
    snap = ContainerSnapshot.create(
        PortRef("t", "in", "v"), script.contract_id, script.content_hash, 1
    )
    out, obs, _, _ = run_script(script, snap)
    assert out.data == 2
    assert obs.effects_observed
    result = check_conformance(
        required_output_type="int",
        provided_data=out.data,
        obs=obs,
        policy=script.specification.policy,
        node_id=script.name,
        contract_id=str(script.contract_id),
    )
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure.property_name == "pure"


def test_record_effect_noop_without_collector():
    record_effect("orphan")  # must not raise
