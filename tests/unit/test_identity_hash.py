from functools import partial

from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.serialization import canonical_serialize, content_hash_of
from acid_engine.level2.specification import Specification
from acid_engine.level3.script.async_module import AsyncScriptModule
from acid_engine.level3.script.module import ScriptModule


def test_same_object_same_hash():
    a = {"x": 1, "y": [3, 2]}
    b = {"y": [3, 2], "x": 1}
    assert canonical_serialize(a) == canonical_serialize(b)
    assert content_hash_of(a) == content_hash_of(b)


def test_change_breaks_hash():
    a = {"x": 1}
    b = {"x": 2}
    assert content_hash_of(a) != content_hash_of(b)


def _script(impl, name="s"):
    return ScriptModule(
        contract_id=ContractId("test", "s"),
        version=Version(1, 0, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=impl,
        name=name,
    )


def test_different_implementation_different_hash():
    a = _script(lambda x: x + 1)
    b = _script(lambda x: x + 100)
    assert a.content_hash != b.content_hash


def test_same_implementation_body_same_hash():
    def f(x):
        return x + 1

    def g(x):
        return x + 1

    assert _script(f).content_hash == _script(g).content_hash


def test_closure_values_are_in_hash():
    def make(n):
        return lambda x: x + n

    assert _script(make(1)).content_hash != _script(make(100)).content_hash


def test_declaration_still_in_hash():
    def f(x):
        return x + 1

    assert _script(f, name="a").content_hash != _script(f, name="b").content_hash


def test_partial_args_are_in_hash():
    def add(x, n):
        return x + n

    assert _script(partial(add, n=1)).content_hash != _script(partial(add, n=100)).content_hash


def test_async_module_hash_includes_implementation():
    async def plus_one(x):
        return x + 1

    async def plus_hundred(x):
        return x + 100

    def make(impl):
        return AsyncScriptModule(
            contract_id=ContractId("test", "a"),
            version=Version(1, 0, 0),
            specification=Specification(),
            input_type="int",
            output_type="int",
            implementation=impl,
            name="a",
        )

    assert make(plus_one).content_hash != make(plus_hundred).content_hash


def test_unmaterialized_artifact_is_missing_not_ref():
    """Ссылка не подменяет канон тела. Нет fn — missing, не dict ArtifactRef."""
    from acid_engine.level3.script.artifact import ArtifactRef

    art = ArtifactRef(
        language="python",
        file="somewhere.py",
        entry="fn",
        canon="ast",
        body_hash="0" * 64,
    )
    missing = _script(None)
    only_ref = ScriptModule(
        contract_id=ContractId("test", "s"),
        version=Version(1, 0, 0),
        specification=Specification(),
        input_type="int",
        output_type="int",
        implementation=None,
        name="s",
        artifact=art,
    )
    assert only_ref.content_hash == missing.content_hash
    assert only_ref._identity_dict()["implementation"] == {"kind": "missing"}
    assert only_ref._identity_dict()["implementation"] != art.to_canonical_dict()
    assert only_ref.content_hash != _script(lambda x: x + 1).content_hash
