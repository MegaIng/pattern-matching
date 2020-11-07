from __future__ import annotations

import sys
from typing import Any

from pattern_matching.pattern_engine import str2pattern
from pattern_matching.withhacks import lookup_name

class match:
    """
    A comprise between ease of use and black magic. Not portable, has weird edge cases, discouraged
    
    Does not inject variables into the containing frame (as `pattern_matching.injecting` does), but looks up name in the containing frame.
    """
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

    def __getattr__(self, item):
        return self.__vars__[item]
        
    def _get(self, name: str):
        return lookup_name(self.__frame__, name)

    def case(self, pattern):
        assert isinstance(pattern, str)
        pt = str2pattern(pattern)
        var = pt.match(self.__value__, self._get)
        if var is not None:
            self.__matched__ = True
            self.__vars__ = var
            return True
        else:
            return False
