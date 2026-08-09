import pytest
from acid_engine.level3.container.types import RecordSchema, RecordField
from acid_engine.level2.conformance import check_conformance
from acid_engine.level3.container.observation import ExecutionObservation
from acid_engine.level3.script.specification import Policy


def test_nested_record_valid():
    inner = RecordSchema(fields=(RecordField("val", "int"),))
    outer = RecordSchema(fields=(
        RecordField("name", "str"),
        RecordField("detail", "record", schema=inner),
    ))
    data = {"name": "X", "detail": {"val": 10}}
    ok, filled = outer.validate(data)
    assert ok
    assert filled["detail"]["val"] == 10

def test_nested_record_invalid_inner():
    inner = RecordSchema(fields=(RecordField("val", "str"),))
    outer = RecordSchema(fields=(
        RecordField("detail", "record", schema=inner),
    ))
    ok, _ = outer.validate({"detail": {"val": 123}})  # int instead of str
    assert not ok

def test_default_value():
    schema = RecordSchema(fields=(
        RecordField("a", "int", optional=True, default=0),
        RecordField("b", "str"),
    ))
    ok, filled = schema.validate({"b": "hello"})
    assert ok
    assert filled["a"] == 0
    assert filled["b"] == "hello"

def test_required_field_missing_no_default():
    schema = RecordSchema(fields=(
        RecordField("x", "int"),
    ))
    ok, _ = schema.validate({})
    assert not ok