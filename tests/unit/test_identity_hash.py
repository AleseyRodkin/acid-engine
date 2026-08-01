from acid_engine.contracts.serialization import canonical_serialize, content_hash_of

def test_same_object_same_hash():
    a = {"x": 1, "y": [3, 2]}
    b = {"y": [3, 2], "x": 1}
    assert canonical_serialize(a) == canonical_serialize(b)
    assert content_hash_of(a) == content_hash_of(b)

def test_change_breaks_hash():
    a = {"x": 1}
    b = {"x": 2}
    assert content_hash_of(a) != content_hash_of(b)