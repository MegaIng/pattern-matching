from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, InitVar
from functools import lru_cache
from itertools import zip_longest
from typing import Callable, Any, Iterable

from lark import Lark, Transformer, v_args, Token


def _get_construction_arguments(t: type, val: Any) -> Iterable[tuple[bool, Any], ...]:
    for f in fields(t):
        if isinstance(f.type, InitVar):
            raise ValueError("Can not match dataclass with InitVar's")
        v = getattr(val, f.name)
        is_optional = f.default == v
        yield is_optional, v


@dataclass(frozen=True)
class Pattern(ABC):
    @abstractmethod
    def match(self, value: Any, get: Callable[[str], Any]) -> tuple[bool, dict[str, Any]]:
        raise NotImplementedError


@dataclass(frozen=True)
class PtVariable(Pattern):
    name: str

    def match(self, value: Any, get: Callable[[str], Any]) -> tuple[bool, dict[str, Any]]:
        return True, {self.name: value}


@dataclass(frozen=True)
class PtConstant(Pattern):
    value: Any

    def match(self, value: Any, get: Callable[[str], Any]) -> tuple[bool, dict[str, Any]]:
        return self.value == value, {}


@dataclass(frozen=True)
class PtConstantVar(Pattern):
    name: str

    def match(self, value: Any, get: Callable[[str], Any]) -> tuple[bool, dict[str, Any]]:
        return get(self.name) == value, {}


@dataclass(frozen=True)
class PtConstruction(Pattern):
    name: str
    args: tuple[Pattern, ...]

    def match(self, value: Any, get: Callable[[str], Any]) -> tuple[bool, dict[str, Any]]:
        t = get(self.name)
        if not isinstance(value, t):
            return False, {}
        else:
            out = {}
            cargs = tuple(_get_construction_arguments(t, value))
            if len(cargs) < len(self.args):
                return False, {}
            for arg, (is_optional, val) in zip_longest(self.args, cargs):
                if arg is None:
                    if not is_optional:
                        return False, {}
                else:
                    cb, cvar = arg.match(val, get)
                    if not cb:
                        return False, {}
                    else:
                        out.update(cvar)
            return True, out


parser = Lark("""
pattern: "None" -> none
       | "True" -> true
       | "False" -> false
       | VAR_NAME -> var
       | CON_NAME -> named_const
       | MIXED_NAME "(" (pattern ("," pattern)* ","?)? ")" -> construction
       | STRING -> string
       | NUMBER -> number

VAR_NAME: "_" | /[a-z][a-z_0-9]*/
CON_NAME: /[A-Z][A-Z0-9_]*/
MIXED_NAME: /[a-zA-Z_][a-zA-Z_0-9]*/
%import common.ESCAPED_STRING -> STRING
%import common.NUMBER
%ignore " "+
""", start='pattern')


@v_args(inline=True)
class ToPattern(Transformer[Pattern]):
    def __default__(self, data, children, meta):
        raise NotImplementedError((data, children, meta))

    def var(self, name: Token) -> Pattern:
        return PtVariable(name.value)

    def construction(self, name: Token, *args: Pattern) -> Pattern:
        return PtConstruction(name.value, args)

    def named_const(self, val: Token):
        return PtConstantVar(val.value)

    def none(self):
        return PtConstant(None)

    def true(self):
        return PtConstant(True)

    def false(self):
        return PtConstant(False)

    def number(self, t: Token):
        return PtConstant(eval(t.value))
    
    def string(self, t: Token):
        return PtConstant(eval(t.value))

@lru_cache()
def parse_pattern(s: str) -> Pattern:
    st = parser.parse(s)
    return ToPattern().transform(st)
