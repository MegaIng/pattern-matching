from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from inspect import getsource
from typing import Any, Callable, Optional, Generic, TypeVar

from pattern_matching.pattern_engine import Pattern, ast2pattern
from pattern_matching.withhacks import WithHack

_matcher_cache: dict[tuple[str, int], _Matcher] = {}


class match(WithHack):
    def __init__(self, value: Any):
        super(match, self).__init__()
        self.value = value

    def __enter__(self):
        super(match, self).__enter__()
        
        fn, fl = self.__frame__.f_code.co_filename, self.__frame__.f_lineno
        try:
            m = _matcher_cache[fn, fl]
        except KeyError:
            with open(fn, encoding="utf-8") as f:
                c = f.read()
            m = _matcher_cache[fn, fl] = _parse_match_stmt(c, fl)
        def exe(vars, a):
            lcls = {}
            r = eval(a, {**self.__frame__.f_globals, **vars}, lcls)
            if r:
                vars |= lcls
                return r
            else:
                return r
            
        l, v = m.match(self.value, self._get_local, exe)
        self._set_context_locals(v)
        if l is None:
            self._dont_execute()
        else:
            self._set_lineno(l)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        return super(match, self).__exit__(exc_type, exc_val, exc_tb)
    



T = TypeVar('T')
U = TypeVar('U')

@dataclass(frozen=True)
class _Matcher(Generic[T, U]):
    cases: tuple[tuple[Pattern, T, Optional[U]], ...]
    otherwise: Optional[T]

    def match(self, val: Any(), get: Callable[[str], Any], exe: Callable[[dict[str, Any], U], bool]) -> tuple[T, dict[str, Any]]:
        for p, l, g in self.cases:
            res = p.match(val, get)
            if res is not None:
                if g is None or exe(res, g):
                    return l, res
        return self.otherwise, {}


def _get_with(a: ast.AST, with_start_line: int) -> ast.With:
    for n in ast.walk(a):
        if isinstance(n, ast.With):
            if n.lineno == with_start_line:
                return n
    else:
        raise ValueError


def _parse_match_stmt(code: str, with_start_line: int) -> _Matcher:
    full_ast = ast.parse(code)
    w = _get_with(full_ast, with_start_line)
    assert len(w.items) == 1
    b = w.body
    cases: list[tuple[Pattern, int, Any]] = []
    while len(b) == 1 and isinstance(b[0], ast.If):
        i, = b
        assert i.test.lineno != i.body[0].lineno
        a = i.test
        if isinstance(a, ast.BoolOp):
            assert isinstance(a.op, ast.And)
            l,r = a.values
            pat, guard = ast2pattern(l), r
            guard = compile(ast.Expression(guard), '<guard>', 'eval')
        else:
            pat, guard = ast2pattern(a), None
        cases.append((pat, i.body[0].lineno, guard))
        b = i.orelse
    if len(b) == 0:
        else_body = None
    else:
        else_body = b[0].lineno
    return _Matcher(tuple(cases), else_body)
