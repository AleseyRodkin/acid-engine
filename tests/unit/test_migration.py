from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.migration import (
    MigrationAction,
    plan_migration,
)
from acid_engine.level3.interface.contract import InterfaceContract


def make_iface(inputs, outputs, constraints=None):
    return InterfaceContract(
        contract_id=ContractId("test", "iface"),
        version=Version(1,0,0),
        inputs=inputs,
        outputs=outputs,
        constraints=constraints or {},
    )


def test_no_changes():
    old = make_iface({"x": "int"}, {"y": "int"})
    new = make_iface({"x": "int"}, {"y": "int"})
    plan = plan_migration(old, new)
    assert len(plan.steps) == 0

def test_add_input():
    old = make_iface({}, {"y": "int"})
    new = make_iface({"x": "int"}, {"y": "int"})
    plan = plan_migration(old, new)
    assert len(plan.steps) == 1
    assert plan.steps[0].action == MigrationAction.ADD_FIELD
    assert plan.steps[0].target == "inputs.x"

def test_remove_output():
    old = make_iface({}, {"y": "int"})
    new = make_iface({}, {})
    plan = plan_migration(old, new)
    assert len(plan.steps) == 1
    assert plan.steps[0].action == MigrationAction.REMOVE_FIELD
    assert plan.steps[0].target == "outputs.y"

def test_change_type():
    old = make_iface({"x": "int"}, {})
    new = make_iface({"x": "float"}, {})
    plan = plan_migration(old, new)
    assert plan.steps[0].action == MigrationAction.CHANGE_TYPE
    assert plan.steps[0].old_value == "int"
    assert plan.steps[0].new_value == "float"

def test_breaking_change():
    old = make_iface({"x": "float"}, {})
    new = make_iface({"x": "int"}, {})
    plan = plan_migration(old, new)
    assert plan.is_breaking
    assert not plan.steps[0].reversible

def test_constraint_change():
    old = make_iface({}, {}, {"pure": False})
    new = make_iface({}, {}, {"pure": True})
    plan = plan_migration(old, new)
    assert len(plan.steps) == 1
    assert plan.steps[0].target == "constraints.pure"

def test_migration_plan_serialization():
    old = make_iface({"x": "int"}, {"y": "int"})
    new = make_iface({"x": "float"}, {"y": "str"})
    plan = plan_migration(old, new)
    d = plan.to_canonical_dict()
    assert d["old_hash"] == old.content_hash
    assert len(d["steps"]) == 2