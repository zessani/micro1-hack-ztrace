from kvcache import serializers


def test_roundtrip():
    assert serializers.loads(serializers.dumps({"b": [1, 2], "a": None})) == {"b": [1, 2], "a": None}


def test_loads_bytes():
    assert serializers.loads(b"[1, 2]") == [1, 2]


def test_loads_none():
    assert serializers.loads(None) is None
