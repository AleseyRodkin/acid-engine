import pytest
from acid_engine.level3.container.types import RecordSchema, RecordField
from acid_engine.level2.conformance import check_conformance
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.script.specification import Policy

def test_record_schema_valid():
    schema = RecordSchema(fields=(
        RecordField("name", "str"),
        RecordField("age", "int"),
    ))
    assert schema.validate({"name": "Alice", "age": 30})

def test_record_schema_missing_required():
    schema = RecordSchema(fields=(
        RecordField("name", "str"),
        RecordField("age", "int", optional=True),
    ))
    ok, _ = schema.validate({"age": 30})  # name missing
    assert not ok

def test_record_schema_optional_missing():
    schema = RecordSchema(fields=(
        RecordField("name", "str"),
        RecordField("age", "int", optional=True),
    ))
    assert schema.validate({"name": "Bob"})

def test_conformance_record():
    obs = ExecutionObservation.create(0, 0.001, "completed")
    schema = RecordSchema(fields=(
        RecordField("x", "int"),
    ))
    result = check_conformance("record", {"x": 1}, obs, Policy(), schema=schema)
    assert result.ok

def test_conformance_record_invalid():
    obs = ExecutionObservation.create(0, 0.001, "completed")
    schema = RecordSchema(fields=(
        RecordField("x", "int"),
    ))
    result = check_conformance("record", {"x": "bad"}, obs, Policy(), schema=schema)
    assert not result.ok