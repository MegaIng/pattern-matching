from __future__ import annotations

import sys
from typing import Any

from pattern_engine import parse
from withhacks import WithHack


class match(WithHack):
    def __init__(self, value: Any):
        self.value = value

    def __enter__(self):
        self._set_context_locals({'__match_obj__': self})
        super(match, self).__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._set_context_locals({'__match_obj__': None})
        return super(match, self).__exit__(exc_type, exc_val, exc_tb)
    
    def _get(self, name: str):
        f = self._get_context_frame()
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
        pt = parse(pattern)
        b,var = pt.match(self.value, self._get)
        if b:
            self._set_context_locals(var)
            return True
        else:
            return False
        


def case(*args, **kwargs):
    f = sys._getframe(1)
    m = f.f_locals.get('__match_obj__')
    if m is None:
        raise ValueError("case() is only valid inside `with match`")
    return m.case(*args, **kwargs)
