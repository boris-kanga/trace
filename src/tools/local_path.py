import os

from pathlib import Path



class LocalPath(Path):
    def __init__(self, path="."):
        self._path = os.path.abspath(str(path))
        super().__init__(self._path)

    def __str__(self):
        return self._path

    def __repr__(self):
        return self._path

    def __sub__(self, other):
        p = self._path
        if isinstance(other, int):
            while other > 0:
                p = os.path.dirname(p)
                other -= 1
        return LocalPath(p)

    def __add__(self, other):
        if isinstance(other, int) and other <= 0:
            return self.__sub__(other)
        if isinstance(other, str):
            if other.startswith(("/", "\\")):
                other = other[1:]
        return LocalPath(
            os.path.join(self._path, str(other))
        )
