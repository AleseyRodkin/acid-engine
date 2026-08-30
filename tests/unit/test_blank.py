from acid_engine.level2.blank import (
    script_identity_blank,
    script_identity_envelope,
    parse_script_identity_blank,
    container_blank,
    plan_blank,
    graph_blank,
    observation_blank,
    conformance_blank,
)
from acid_engine.level2.serialization import canonical_serialize, content_hash_of
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.specification import Specification
from acid_engine.level2.conformance import (
    ConformanceResult,
    ConformanceStatus,
    ConformanceLevel,
)
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.container.port import PortRef
from acid_engine.level3.container.snapshot import ContainerSnapshot
from acid_engine.level3.bootstrap.plan_lock import PlanLock
from acid_engine.level3.script.modes import ExecutionMode
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.container.observation import ExecutionObservation


def _script(impl, name="plus"):
    return ScriptModule(
        contract_id=ContractId("t", name),
        version=Version(0, 1, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=impl,
        name=name,
    )


def plus_one(x):
    return x + 1


def plus_hundred(x):
    return x + 100


def test_plus_one_blank_hash_equals_content_hash():
    script = _script(plus_one, name="plus")
    blank = script_identity_blank(script)
    assert content_hash_of(blank) == script.content_hash
    assert "content_hash" not in blank


def test_plus_one_vs_plus_hundred_different_blank_hash():
    a = _script(plus_one, name="plus")
    b = _script(plus_hundred, name="plus")
    assert content_hash_of(script_identity_blank(a)) != content_hash_of(
        script_identity_blank(b)
    )
    assert a.content_hash != b.content_hash


def test_same_body_different_name_different_hash():
    a = _script(plus_one, name="a")
    b = _script(plus_one, name="b")
    assert content_hash_of(script_identity_blank(a)) != content_hash_of(
        script_identity_blank(b)
    )


def test_envelope_schema_kind_not_in_identity_hash():
    script = _script(plus_one)
    ident = script_identity_blank(script)
    env = script_identity_envelope(script)
    assert env["schema"] == "acid.blank.script.v1"
    assert env["kind"] == "script"
    assert env["identity"] == ident
    assert content_hash_of(ident) == script.content_hash
    assert content_hash_of(env) != content_hash_of(ident)


def test_serialize_blank_has_no_callable():
    script = _script(plus_one)
    blank = script_identity_blank(script)
    text = canonical_serialize(blank)
    assert "function" not in text
    assert not callable(blank["implementation"])


def test_unknown_key_is_error():
    script = _script(plus_one)
    ident = dict(script_identity_blank(script))
    ident["extra_field"] = 1
    try:
        parse_script_identity_blank(ident)
        assert False, "expected unknown key error"
    except ValueError as e:
        assert "unknown key" in str(e)


def test_parse_envelope_roundtrip_identity():
    script = _script(plus_one)
    env = script_identity_envelope(script)
    parsed = parse_script_identity_blank(env)
    assert content_hash_of(parsed) == script.content_hash


def test_container_blank_stable():
    snap = ContainerSnapshot.create(
        port_ref=PortRef("m", "input", "value"),
        contract_id=ContractId("t", "plus"),
        contract_hash="abc",
        data=3,
    )
    a = container_blank(snap)
    b = container_blank(snap)
    assert a == b
    assert content_hash_of(a) == content_hash_of(b)
    canonical_serialize(a)


def test_plan_blank_stable_and_matches_lock_hash():
    plan = PlanLock.create(
        plan_id="p1",
        interface_contract_hash="iface",
        resolved_policies={"pure": True},
        module_hashes={"plus": "h"},
        execution_mode=ExecutionMode.NORMAL,
    )
    a = plan_blank(plan)
    b = plan_blank(plan)
    assert a == b
    assert "created_at" not in a
    assert content_hash_of(a) == plan.content_hash


def test_graph_blank_has_no_payload():
    g = DependencyGraph()
    g.add_node("a", payload=plus_one)
    g.add_node("b", payload=plus_hundred)
    g.add_edge("a", "b")
    blank = graph_blank(g)
    canonical_serialize(blank)
    assert blank["nodes"] == ["a", "b"]
    assert blank["edges"] == [{"source": "a", "target": "b"}]


def test_observation_and_conformance_blank_json_safe():
    obs = ExecutionObservation.create(0.0, 0.001, "completed")
    ob = observation_blank(obs)
    assert "run_id" not in ob
    canonical_serialize(ob)
    conf = ConformanceResult(
        status=ConformanceStatus.SKIPPED,
        level=ConformanceLevel.STRUCTURAL,
        message="no facts",
    )
    canonical_serialize(conformance_blank(conf))
