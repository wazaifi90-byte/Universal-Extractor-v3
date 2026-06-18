import os
import sys
import time

_HAS_TQDM = False
try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    pass


class ProgressTracker:
    def __init__(self, total=0, desc="Processing", unit="B", disable=False):
        self.total = total
        self.current = 0
        self.desc = desc
        self.unit = unit
        self.disable = disable
        self._tqdm = None
        self._start_time = None
        self._enabled = not disable and _HAS_TQDM

    def __enter__(self):
        if self._enabled:
            self._tqdm = tqdm(
                total=self.total,
                desc=self.desc,
                unit=self.unit,
                unit_scale=True,
                leave=True,
                ncols=80,
                mininterval=0.1,
            )
        self._start_time = time.time()
        return self

    def __exit__(self, *args):
        if self._tqdm:
            self._tqdm.close()

    def update(self, n=1):
        self.current += n
        if self._tqdm:
            self._tqdm.update(n)

    def set_total(self, total):
        self.total = total
        if self._tqdm:
            self._tqdm.total = total

    def set_desc(self, desc):
        self.desc = desc
        if self._tqdm:
            self._tqdm.set_description(desc)

    def elapsed(self):
        if self._start_time:
            return time.time() - self._start_time
        return 0

    @property
    def has_tqdm(self):
        return self._enabled
