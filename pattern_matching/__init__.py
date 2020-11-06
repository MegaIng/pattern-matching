from __future__ import annotations

from typing import Any

from pattern_matching.pattern_engine import str2pattern


class _Match:
    def __init__(self, matcher: Matcher, value: Any):
        self.__matcher__ = matcher
        self.__value__ = value
        self.__vars__ = None

    def __getattr__(self, item):
        return self.__vars__[item]

    def __matmul__(self, other: str):
        return self.case(other)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def case(self, pattern: str):
        assert isinstance(pattern, str)
        pt = str2pattern(pattern)
        var = pt.match(self.__value__, self.__matcher__._get)
        if var is not None:
            self.__vars__ = var
            return True
        else:
            return False
    
    def __call__(self, pattern: str):
        return self.case(pattern)


class Matcher:
    """
    A portable match statement.
    
    This is what should always be used. It forces you to clearly define all accessible names, including constants.
    """
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