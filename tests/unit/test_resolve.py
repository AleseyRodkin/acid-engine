import os
import tempfile
from pathlib import Path

from acid_engine.level2.conformance import ConformanceStatus
from acid_engine.level2.identity import ContractId, Version
from acid_engine.level2.implementation_canon import canonical_implementation
from acid_engine.level2.serialization import content_hash_of
from acid_engine.level2.specification import Policy, Specification
from acid_engine.level3.script.artifact import ArtifactRef
from acid_engine.level3.script.module import ScriptModule
from acid_engine.level3.script.resolve import resolve_script
from acid_engine.level3.script.runner import execute_plan, lock_for_script
from acid_engine.worker import live_toolchain

BODY = '''def plus_one(x):
    return x + 1
'''


def _iface_plan(script):
    return lock_for_script(script)


def _script(**kwargs):
    kw = dict(
        contract_id=ContractId("t", "s"),
        version=Version(1, 0, 0),
        specification=Specification(policy=Policy(max_latency_ms=500)),
        input_type="int",
        output_type="int",
        name="s",
    )
    kw.update(kwargs)
    return ScriptModule(**kw)


def plus_one(x):
    return x + 1


def test_resolve_python_file_and_run():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "plus.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(BODY)
        # body_hash empty: 2b allows run without hash check
        art = ArtifactRef(
            language="python",
            file=path,
            entry="plus_one",
            canon="ast",
            body_hash="",
        )
        script = _script(implementation=None, artifact=art)
        iface, plan = _iface_plan(script)
        result = execute_plan(iface, plan, script, 3, toolchain=live_toolchain())
        assert result.ok
        assert result.data == 4


def test_unknown_language_is_fail_not_eval():
    art = ArtifactRef(
        language="javascript",
        file="x.js",
        entry="fn",
        canon="opaque",
        body_hash="",
    )
    script = _script(implementation=None, artifact=art)
    iface, plan = _iface_plan(script)
    result = execute_plan(iface, plan, script, 1, toolchain=live_toolchain())
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure.property_name == "language"
    assert result.data is None


def test_broken_file_is_fail():
    art = ArtifactRef(
        language="python",
        file="/tmp/acid_missing_artifact_nope.py",
        entry="plus_one",
        canon="ast",
        body_hash="",
    )
    script = _script(implementation=None, artifact=art)
    iface, plan = _iface_plan(script)
    result = execute_plan(iface, plan, script, 1, toolchain=live_toolchain())
    assert not result.ok
    assert result.status == ConformanceStatus.FAIL
    assert result.failure.property_name == "artifact"


def test_missing_impl_and_artifact_is_skipped():
    script = _script(implementation=None, artifact=None)
    iface, plan = _iface_plan(script)
    result = execute_plan(iface, plan, script, 1, toolchain=live_toolchain())
    assert result.status == ConformanceStatus.SKIPPED
    assert not result.ok
    assert result.data is None


def test_callable_still_preferred_over_artifact():
    art = ArtifactRef(
        language="javascript",
        file="nope.js",
        entry="x",
        canon="opaque",
        body_hash="",
    )
    script = _script(implementation=plus_one, artifact=art)
    iface, plan = _iface_plan(script)
    result = execute_plan(iface, plan, script, 2, toolchain=live_toolchain())
    assert result.ok
    assert result.data == 3


def test_materialize_artifact_hash_equals_callable():
    from acid_engine.level3.script.resolve import materialize_script

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "plus.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(BODY)
        art = ArtifactRef(
            language="python",
            file=path,
            entry="plus_one",
            canon="ast",
            body_hash="",
        )
        only_ref = _script(implementation=None, artifact=art)
        native = _script(implementation=plus_one)
        got = materialize_script(only_ref)
        assert got.content_hash == native.content_hash
        assert callable(got.implementation)


def test_lock_after_materialize_matches_callable_not_naked_ref():
    from acid_engine.level3.script.resolve import materialize_script

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "plus.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(BODY)
        art = ArtifactRef(
            language="python",
            file=path,
            entry="plus_one",
            canon="ast",
            body_hash="",
        )
        only_ref = _script(implementation=None, artifact=art)
        native = _script(implementation=plus_one)
        assert only_ref.content_hash != native.content_hash
        _, plan = lock_for_script(only_ref)
        frozen = materialize_script(only_ref)
        assert frozen.content_hash == native.content_hash
        assert plan.module_hashes[only_ref.name] == native.content_hash


def test_source_canon_matches_live_callable():
    from acid_engine.level2.implementation_canon import (
        canonical_implementation_from_source,
    )

    preview = canonical_implementation_from_source(BODY.encode("utf-8"), "plus_one")
    assert preview is not None
    assert preview == canonical_implementation(plus_one)


def test_artifact_body_hash_mismatch_does_not_import(tmp_path: Path) -> None:
    py = tmp_path / "plus.py"
    marker = tmp_path / "pwned"
    approved = content_hash_of(canonical_implementation(plus_one))
    py.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('pwn')\n"
        "def plus_one(x):\n    return x + 99\n",
        encoding="utf-8",
    )
    art = ArtifactRef(
        language="python",
        file=str(py),
        entry="plus_one",
        canon="ast",
        body_hash=approved,
    )
    script = _script(implementation=None, artifact=art)
    fn, err = resolve_script(script)
    assert fn is None
    assert err is not None
    assert err.startswith("body_hash")
    assert not marker.exists()


def test_artifact_source_hash_mismatch_does_not_import(tmp_path: Path) -> None:
    import hashlib

    py = tmp_path / "plus.py"
    marker = tmp_path / "pwned"
    honest = BODY.encode("utf-8")
    py.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('pwn')\n" + BODY,
        encoding="utf-8",
    )
    art = ArtifactRef(
        language="python",
        file=str(py),
        entry="plus_one",
        canon="ast",
        body_hash=content_hash_of(canonical_implementation(plus_one)),
        source_hash=hashlib.sha256(honest).hexdigest(),
    )
    script = _script(implementation=None, artifact=art)
    fn, err = resolve_script(script)
    assert fn is None
    assert err is not None
    assert err.startswith("source_hash")
    assert not marker.exists()


def test_artifact_body_hash_match_still_loads(tmp_path: Path) -> None:
    py = tmp_path / "plus.py"
    py.write_text(BODY, encoding="utf-8")
    approved = content_hash_of(canonical_implementation(plus_one))
    art = ArtifactRef(
        language="python",
        file=str(py),
        entry="plus_one",
        canon="ast",
        body_hash=approved,
    )
    script = _script(implementation=None, artifact=art)
    fn, err = resolve_script(script)
    assert err is None
    assert fn is not None
    assert fn(3) == 4
