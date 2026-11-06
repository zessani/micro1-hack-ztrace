"""A small in-memory manifest registry."""


class Registry:
    def __init__(self, fetch):
        self._fetch = fetch
        self._manifests = {}

    def manifest(self, name):
        if name not in self._manifests:
            self._manifests[name] = self._fetch(name)
        return self._manifests[name]

    def names(self):
        return sorted(self._manifests)
