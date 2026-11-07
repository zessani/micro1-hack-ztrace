"""Hit/miss counters."""


class CacheStats:
    def __init__(self):
        self.hits = 0
        self.misses = 0

    def record(self, hit):
        if hit:
            self.hits += 1
        else:
            self.misses += 1

    @property
    def total(self):
        return self.hits + self.misses

    @property
    def hit_rate(self):
        return self.hits / self.total if self.total else 0.0

    def reset(self):
        self.hits = 0
        self.misses = 0
