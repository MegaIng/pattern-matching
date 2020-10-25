from __future__ import annotations

from typing import Any

from pattern_engine import parse_pattern


class _Match:
    def __init__(self, matcher: Matcher, value: Any):
        self.__matcher__ = matcher
        self.__value__ = value
        self.__matched__ = False
        self.__vars__ = None

    def __getattribute__(self, item):
        if item[:2] == item[-2:] == '__':
            return super(_Match, self).__getattribute__(item)
        if self.__matched__:
            return self.__vars__[item]
        else:
            return super(_Match, self).__getattribute__(item)

    def __matmul__(self, other: str):
        return self.case(other)

    def case(self, pattern: str):
        assert isinstance(pattern, str)
        pt = parse_pattern(pattern)
        b, var = pt.match(self.__value__, self.__matcher__._get)
        if b:
            self.__matched__ = True
            self.__vars__ = var
            return True
        else:
            return False


class Matcher:
    def __init__(self, *args, **kwargs):
        self.__names__ = kwargs
        for a in args:
            try:
                self.__names__[a.__name__] = a
            except AttributeError:
                raise ValueError("Can not use values that don't have a `__name__` attribute (functions, classes) without specifying a name")

    def _get(self, name: str):
        try:
            return self.__names__[name]
        except KeyError:
            raise NameError

    def __call__(self, value: Any):
        return _Match(self, value)
