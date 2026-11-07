"""In-process LRU cache."""
import logging
from collections import OrderedDict

log = logging.getLogger(__name__)


class LRUCache:
    def __init__(self, capacity=128):
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key, default=None):
        if key not in self._data:
            return default
        return self._data[key]

    def set(self, key, value):
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.capacity:
            evicted, _ = self._data.popitem(last=False)
            log.warning("evicted %r (capacity %d)", evicted, self.capacity)

    def clear(self):
        self._data.clear()

    def keys(self):
        return list(self._data)

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data
