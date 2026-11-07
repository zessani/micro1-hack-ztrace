import datetime

import pytest

from kvcache import serializers


@pytest.mark.parametrize("value", [0, 1, -3, 2.5, "", "text", [], [1, 2], {}, {"a": 1}, True, False, None])
def test_roundtrip_json_types(value):
    assert serializers.loads(serializers.dumps(value)) == value


def test_loads_bytes():
    assert serializers.loads(b'{"a": 1}') == {"a": 1}


def test_loads_none():
    assert serializers.loads(None) is None


def test_dumps_sorts_keys():
    assert serializers.dumps({"b": 1, "a": 2}) == '{"a": 2, "b": 1}'


def test_datetime_is_iso_string():
    stamp = datetime.datetime(2024, 5, 1, 12, 30, 0)
    assert serializers.loads(serializers.dumps({"at": stamp})) == {"at": "2024-05-01T12:30:00"}


def test_date_is_iso_string():
    assert serializers.loads(serializers.dumps(datetime.date(2024, 5, 1))) == "2024-05-01"
