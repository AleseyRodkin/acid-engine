from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.implementation_canon import canonical_implementation
from acid_engine.level2.specification import Specification
from acid_engine.level3.script.artifact import (
    CANON_KINDS,
    ArtifactRef,
    artifact_ref_from_callable,
)
from acid_engine.level3.script.module import ScriptModule


def plus_one(x):
    return x + 1


def _script(impl=plus_one, artifact=None, name="s"):
    return ScriptModule(
        contract_id=ContractId("test", "s"),
        version=Version(1, 0, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=impl,
        name=name,
        artifact=artifact,
    )


def test_artifact_optional_does_not_change_hash():
    bare = _script()
    ref = artifact_ref_from_callable(plus_one)
    with_ref = _script(artifact=ref)
    assert bare.content_hash == with_ref.content_hash
    assert "artifact" not in bare._identity_dict()
    assert "artifact" not in with_ref._identity_dict()


def test_artifact_canon_matches_implementation_kind():
    impl = canonical_implementation(plus_one)
    ref = artifact_ref_from_callable(plus_one)
    assert ref.language == "python"
    assert ref.canon == impl["kind"]
    assert ref.canon in CANON_KINDS
    assert ref.entry
    assert ref.body_hash


def test_artifact_invalid_canon_rejected():
    try:
        ArtifactRef(
            language="python",
            file="x.py",
            entry="f",
            canon="json-schema",
            body_hash="0" * 64,
        )
        assert False, "expected ValueError"
    except ValueError as e:
        assert "canon" in str(e)


def test_implementation_still_required_callable():
    script = _script()
    assert callable(script.implementation)
    assert script.artifact is None
