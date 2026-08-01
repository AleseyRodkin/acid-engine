from acid_engine.contracts.attributes import (
    Attribute, AttributeSet, Origin, Mutability, ValueKind,
)
from acid_engine.contracts.serialization import canonical_serialize, content_hash_of

def test_attribute_creation():
    a = Attribute(
        name="precision",
        value=0.95,
        origin=Origin.USER,
        mutability=Mutability.LOCKED,
        value_kind=ValueKind.FACTUAL,
    )
    assert a.name == "precision"
    assert a.value == 0.95
    assert a.origin == Origin.USER
    assert a.mutability == Mutability.LOCKED
    assert a.value_kind == ValueKind.FACTUAL

def test_attribute_deterministic_serialization():
    a1 = Attribute(name="x", value=1, origin=Origin.SYSTEM, mutability=Mutability.EDITABLE, value_kind=ValueKind.COMPUTED)
    a2 = Attribute(name="x", value=1, origin=Origin.SYSTEM, mutability=Mutability.EDITABLE, value_kind=ValueKind.COMPUTED)
    assert canonical_serialize(a1) == canonical_serialize(a2)
    assert content_hash_of(a1) == content_hash_of(a2)

def test_attribute_hash_changes():
    a1 = Attribute(name="x", value=1)
    a2 = Attribute(name="x", value=2)
    assert content_hash_of(a1) != content_hash_of(a2)

def test_attribute_set():
    attrs = AttributeSet(attributes=(
        Attribute("a", 1),
        Attribute("b", 2),
    ))
    assert attrs.get("a").value == 1
    assert attrs.get("missing") is None

def test_attribute_set_deterministic():
    set1 = AttributeSet(attributes=(Attribute("a", 1), Attribute("b", 2)))
    set2 = AttributeSet(attributes=(Attribute("b", 2), Attribute("a", 1)))
    assert canonical_serialize(set1) == canonical_serialize(set2)
    assert content_hash_of(set1) == content_hash_of(set2)