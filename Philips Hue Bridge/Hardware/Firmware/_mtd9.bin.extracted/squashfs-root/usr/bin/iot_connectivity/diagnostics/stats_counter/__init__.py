import math
import sys


class StatsCounter:
    def __init__(self, limit):
        # add extras for under and overflow
        self._num_bins = self._which_bin(limit) + 2
        self.clear()

    def _which_bin(self, x):
        if x <= 0:
            return 0
        return math.frexp(x)[1]

    def clear(self):
        self._bins = [0] * self._num_bins
        self._min = sys.maxsize  # allow 0 as a valid min
        self._max = 0
        self._total = 0
        self._count = 0

    def add(self, x):
        self._count += 1
        self._total += x

        if x < self._min:
            self._min = x

        if x > self._max:
            self._max = x

        b = self._which_bin(x)
        if b >= self._num_bins:  # overflow case
            b = self._num_bins - 1

        self._bins[b] += 1

    def get(self):
        return {
            "min": self._min if self._min != sys.maxsize else 0,
            "max": self._max,
            "total": self._total,
            "count": self._count,
            "histogram": self._bins,
        }
