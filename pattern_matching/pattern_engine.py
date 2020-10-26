from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, InitVar, is_dataclass
from functools import lru_cache
from itertools import zip_longest, takewhile
from typing import Callable, Any, Iterable, Sequence, Optional, Mapping

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
        yield from _dataclass_construction(t, val)
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
                        out |= cvar
            return out


def _match_all(pts: tuple[Pattern, ...], value: Any, get) -> Optional[dict[str, Any]]:
    out = {}
    for e, v in zip_longest(pts, value):
        cvar = e.match(v, get)
        if cvar is None:
            return None
        else:
            out |= cvar
    return out


@dataclass(frozen=True)
class PtFixedSequence(Pattern):
    elements: tuple[Pattern, ...]

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        if not isinstance(value, Sequence):
            return None
        if len(value) != len(self.elements):
            return None
        return _match_all(self.elements, value, get)

@dataclass(frozen=True)
class PtMapping(Pattern):
    elements: tuple[tuple[Any, Pattern], ...]
    star: str = None

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        if not isinstance(value, Mapping):
            return None
        out = {}
        used = set()
        for kp, vp in self.elements:
            if isinstance(kp, PtConstantVar):
                kp = get(kp.name)
            if kp not in value:
                return None
            cvar = vp.match(value[kp], get)
            if cvar is None:
                return None
            out |= cvar
            used.add(kp)
        if self.star is not None:
            out[self.star] = {k:v for k, v in value.items() if k not in used}
        return out


@dataclass(frozen=True)
class PtVariableSequence(Pattern):
    pre: tuple[Pattern, ...]
    star: str
    post: tuple[Pattern, ...]

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        if not isinstance(value, Sequence):
            return None
        if len(value) < len(self.pre) + len(self.post):
            return None
        pre_val = value[:len(self.pre)]
        post_val = value[len(value) - len(self.post):]  # -len(self.post) is not enough, since `-0` is equivalent to `0`
        star_val = value[len(self.pre):len(value) - len(self.post)]
        pre_out = _match_all(self.pre, pre_val, get)
        if pre_out is None:
            return None
        post_out = _match_all(self.post, post_val, get)
        if post_out is None:
            return None

        return pre_out | {self.star: star_val} | post_out


parser = Lark("""
pattern: literal -> constant
       | VAR_NAME -> var
       | MIXED_NAME "(" (pattern ("," pattern)* ","?)? ")" -> construction
       | "[" _sequence "]" -> sequence
       | "(" (seq_item "," _sequence)? ")" -> sequence
       | "{" (mapping_item ("," mapping_item)* ","?)?"}" -> mapping
       | "{" (mapping_item ("," mapping_item)* ",")? "**" VAR_NAME ","? "}" -> mapping_star


literal: "None" -> none
       | "True" -> true
       | "False" -> false
       | CON_NAME -> named_const
       | STRING -> string
       | NUMBER -> number

mapping_item: literal ":" pattern

_sequence: (seq_item ("," seq_item)* ","?)?
?seq_item: pattern
         | "*" VAR_NAME -> start_pattern

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
        return None

    def true(self):
        return True

    def false(self):
        return False

    def number(self, t: Token):
        return eval(t.value)

    def string(self, t: Token):
        return eval(t.value)
    
    def constant(self, val: Any):
        if isinstance(val, Pattern):
            return val
        else:
            return PtConstant(val)
    
    def mapping(self, *elements):
        return PtMapping(elements)
    
    def mapping_star(self, *elements):
        return PtMapping(elements[:-1], elements[-1].value)

    def mapping_item(self, key: Any, val: Any):
        return key, val

    def sequence(self, *children: Pattern):
        if any(isinstance(c, str) for c in children):
            pre = tuple(takewhile(lambda c: not isinstance(c, str), children))
            star = children[len(pre)]
            post = children[len(pre) + 1:]
            assert not any(isinstance(c, str) for c in post)
            return PtVariableSequence(pre, star, post)
        else:
            return PtFixedSequence(children)

    def start_pattern(self, name: Token):
        return name.value


@lru_cache()
def parse_pattern(s: str) -> Pattern:
    st = parser.parse(s)
    return ToPattern().transform(st)
