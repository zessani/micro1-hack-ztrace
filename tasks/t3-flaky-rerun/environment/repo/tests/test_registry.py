from pkgver.registry import Registry

_cold_start = {"calls": 0}


def _flaky_fetch(name):
    _cold_start["calls"] += 1
    if _cold_start["calls"] == 1:
        raise TimeoutError("manifest backend cold start")
    return {"name": name}


def test_manifest_cached():
    calls = []
    reg = Registry(lambda n: calls.append(n) or {"name": n})
    reg.manifest("a")
    reg.manifest("a")
    assert calls == ["a"]


def test_manifest_fetch_after_cold_start():
    reg = Registry(_flaky_fetch)
    assert reg.manifest("pkg") == {"name": "pkg"}


def test_names_sorted():
    reg = Registry(lambda n: {})
    reg.manifest("b")
    reg.manifest("a")
    assert reg.names() == ["a", "b"]
