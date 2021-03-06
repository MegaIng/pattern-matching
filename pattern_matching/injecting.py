from __future__ import annotations

import sys
from typing import Any

from pattern_matching.pattern_engine import str2pattern
from pattern_matching.withhacks import WithHack, lookup_name


class match(WithHack):
    """
    A fully magic match statement that automatically injects variables into the frame.
    """
    def __init__(self, value: Any):
        super(match, self).__init__()
        self.value = value

    def __enter__(self):
        super(match, self).__enter__()
        self._set_context_locals({'__match_obj__': self})
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._set_context_locals({'__match_obj__': None})
        return super(match, self).__exit__(exc_type, exc_val, exc_tb)

    def _get(self, name: str):
        return lookup_name(self.__frame__, name)

    def case(self, pattern):
        assert isinstance(pattern, str)
        pt, g = str2pattern(pattern)
        assert g is None
        var = pt.match(self.value, self._get)
        if var is not None:
            self._set_context_locals(var)
            return True
        else:
            return False


def case(*args, **kwargs):
    f = sys._getframe(1)
    m = lookup_name(f, '__match_obj__')
    if m is None:
        raise ValueError("case() is only valid inside `with match`")
    return m.case(*args, **kwargs)
