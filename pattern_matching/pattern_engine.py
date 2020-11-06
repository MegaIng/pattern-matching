from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, InitVar, is_dataclass
from functools import lru_cache
from itertools import zip_longest, takewhile
from typing import Callable, Any, Iterable, Sequence, Optional, Mapping

from lark import Lark, Transformer, v_args, Token

from pattern_matching.match_args_data import match_args_and_kwargs


@dataclass(frozen=True)
class Pattern(ABC):
    @abstractmethod
    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        raise NotImplementedError


@dataclass(frozen=True)
class PtCaptureAs(Pattern):
    base: Pattern
    name: str

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        r = self.base.match(value, get)
        if r is not None:
            r[self.name] = value
        return r

@dataclass(frozen=True)
class PtCapture(Pattern):
    name: str

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        return {self.name: value}


@dataclass(frozen=True)
class PtOr(Pattern):
    options: tuple[Pattern, ...]

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        for o in self.options:
            r = o.match(value, get)
            if r is not None:
                return r
        else:
            return None

@dataclass(frozen=True)
class PtConstant(Pattern, ABC):
    
    @abstractmethod
    def calc_value(self, get: Callable[[str], Any]) -> Any:
        raise NotImplementedError
    
    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        return {} if self.calc_value(get) == value else None


@dataclass(frozen=True)
class PtLiteral(PtConstant):
    value: Any
    
    def calc_value(self, get: Callable[[str], Any]) -> Any:
        return self.value


@dataclass(frozen=True)
class PtValue(PtConstant):
    attributes: tuple[str, ...]
    
    def calc_value(self, get: Callable[[str], Any]) -> Any:
        value = get(self.attributes[0])
        for a in self.attributes[1:]:
            value = getattr(value, a)
        return value

@dataclass(frozen=True)
class PtClass(Pattern):
    cls: PtValue
    args: tuple[Pattern, ...]
    kwargs: tuple[tuple[str, Pattern], ...]
    
    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        t = self.cls.calc_value(get)
        assert isinstance(t, type), t
        if not isinstance(value, t):
            return None
        pairs = match_args_and_kwargs(t, value, self.args, self.kwargs)
        if pairs is None:
            return None
        out = {}
        for pat, val in pairs:
            pat: Pattern
            res = pat.match(val, get)
            if res is None:
                return None
            out |= res
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

_missing_marker = object()

@dataclass(frozen=True)
class PtMapping(Pattern):
    elements: tuple[tuple[PtConstant, Pattern], ...]
    star: str = None

    def match(self, value: Any, get: Callable[[str], Any]) -> Optional[dict[str, Any]]:
        if not isinstance(value, Mapping):
            return None
        out = {}
        used = set()
        for kp, vp in self.elements:
            key = kp.calc_value(get)
            if key not in value:
                return None
            val = value.get(key, _missing_marker)
            if val is _missing_marker:
                return None
            cvar = vp.match(val, get)
            if cvar is None:
                return None
            out |= cvar
            used.add(kp)
        if self.star is not None:
            out[self.star] = {k: v for k, v in value.items() if k not in used}
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
?start: seq_item "," _sequence -> sequence | as_pattern
?as_pattern: or_pattern ("as" NAME)?
?or_pattern: closed_pattern ("|" closed_pattern)*
?closed_pattern: literal
               | NAME -> capture
               | attr
               | "(" as_pattern ")"
               | "[" _sequence "]" -> sequence
               | "(" (seq_item "," _sequence)? ")" -> sequence
               | "{" (mapping_item ("," mapping_item)* ","?)?"}" -> mapping
               | "{" (mapping_item ("," mapping_item)* ",")? "**" NAME ","? "}" -> mapping_star
               | class_pattern


literal: "None" -> none
       | "True" -> true
       | "False" -> false
       | STRING -> string
       | NUMBER -> number

attr: NAME ("." NAME)+ -> value

name_or_attr: NAME ("." NAME)* -> value

mapping_item: (literal|attr) ":" as_pattern

_sequence: (seq_item ("," seq_item)* ","?)?
?seq_item: as_pattern
         | "*" NAME -> star_pattern

class_pattern: name_or_attr "(" [arguments ","?] ")"
arguments: pos ["," keyws] | keyws

pos: as_pattern ("," as_pattern)*
keyws: keyw ("," keyw)*
keyw: NAME "=" as_pattern

NAME: /[a-zA-Z_][a-zA-Z_0-9]*/
%import common.ESCAPED_STRING -> STRING
%import common.NUMBER
%ignore " "+
""", start='start', maybe_placeholders=True)


@v_args(inline=True)
class Lark2Pattern(Transformer[Pattern]):
    def __default__(self, data, children, meta):
        raise NotImplementedError((data, children, meta))
    
    def value(self, *names):
        return PtValue(tuple(v.value for v in names))

    def none(self):
        return PtLiteral(None)

    def true(self):
        return PtLiteral(True)

    def false(self):
        return PtLiteral(False)

    def number(self, t: Token):
        return PtLiteral(eval(t.value))

    def string(self, t: Token):
        return PtLiteral(eval(t.value))
    
    def pos(self, *children: Pattern):
        return children
    
    def arguments(self, *ch):
        if len(ch) == 2:
            pos, kw = ch
        else:
            pos, kw = None, *ch
        pos = pos or ()
        kw = kw or ()
        return pos, kw

    def class_pattern(self, cls, args):
        return PtClass(cls, *args)
    
    def capture(self, name: Token):
        return PtCapture(name.value)

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

    def star_pattern(self, n: Token):
        return n.value


@lru_cache()
def str2pattern(s: str) -> Pattern:
    st = parser.parse(s)
    return Lark2Pattern().transform(st)
