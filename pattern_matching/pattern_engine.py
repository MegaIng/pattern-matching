from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, InitVar, is_dataclass
from functools import lru_cache
from itertools import zip_longest
from typing import Callable, Any, Iterable, Sequence, Optional

from lark import Lark, Transformer, v_args, Token


def _self_construction(t, val) -> Iterable[tuple[bool, Any]]:
    return not bool(val), val


KNOWN_CONSTRUCTIONS = {
    list: _self_construction, set: _self_construction, dict: _self_construction, frozenset: _self_construction, tuple: _self_construction,
    bool: _self_construction, float: _self_construction, int: _self_construction, str: _self_construction, bytes: _self_construction,
    bytearray: _self_construction,
}

def _dataclass_construction(t, val) -> Iterable[tuple[bool, Any]]:
    for f in fields(t):
        if isinstance(f.type, InitVar) or not f.init:
            raise ValueError("Can not match dataclass with InitVar's or `field(init=False)`")
        v = getattr(val, f.name)
        is_optional = f.default == v
        yield is_optional, v


def _get_construction(t, val: Any) -> Iterable[tuple[bool, Any], ...]:
    if t in KNOWN_CONSTRUCTIONS:
        yield from KNOWN_CONSTRUCTIONS[t](t, val)
    elif is_dataclass(t):
        return _dataclass_construction(t, val)
    else:
        try:
            yield from t.__get_construction__(val)
        except AttributeError:
            raise TypeError(f"Can not get construction for {t}")


@dataclass(frozen=True)
class Pattern(ABC):
    @abstractmethod
    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        raise NotImplementedError


@dataclass(frozen=True)
class PtVariable(Pattern):
    name: str

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        return {self.name: value}


@dataclass(frozen=True)
class PtConstant(Pattern):
    value: Any

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        return {} if self.value == value else None


@dataclass(frozen=True)
class PtConstantVar(Pattern):
    name: str

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        return {} if get(self.name) == value else None


@dataclass(frozen=True)
class PtConstruction(Pattern):
    name: str
    args: tuple[Pattern, ...]

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        t = get(self.name)
        if not isinstance(value, t):
            return None
        else:
            out = {}
            cargs = tuple(_get_construction(t, value))
            if len(cargs) < len(self.args):
                return None
            for arg, (is_optional, val) in zip_longest(self.args, cargs):
                if arg is None:
                    if not is_optional:
                        return None
                else:
                    cvar = arg.match(val, get)
                    if cvar is None:
                        return None
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
