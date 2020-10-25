from __future__ import annotations

import sys
from typing import Any

from pattern_engine import parse_pattern


class match:
    def __init__(self, value: Any):
        self.__value__ = value
        self.__matched__ = False
        self.__frame__ = None
        self.__vars__ = None

    def __enter__(self):
        self.__frame__ = sys._getframe(1)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def __getattribute__(self, item):
        if item[:2] == item[-2:] == '__':
            return super(match, self).__getattribute__(item)
        if self.__matched__:
            return self.__vars__[item]
        else:
            return super(match, self).__getattribute__(item)
        
    def _get(self, name: str):
        f = self.__frame__
        if name in f.f_locals:
            return f.f_locals[name]
        elif name in f.f_globals:
            return f.f_globals[name]
        elif name in f.f_builtins:
            return f.f_builtins[name]
        else:
            raise NameError(name)

    def case(self, pattern):
        assert isinstance(pattern, str)
        pt = parse_pattern(pattern)
        b, var = pt.match(self.__value__, self._get)
        if b:
            self.__matched__ = True
            self.__vars__ = var
            return True
        else:
            return False
