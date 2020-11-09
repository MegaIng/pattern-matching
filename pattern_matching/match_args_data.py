"""
Provides facilities to deal with `__match_args__` as defined in PEP-634.
Since we can't modify the stdlib to correctly report `__match_args__` for those classes (especially dataclass/namedtuple),
we also have extra work that is not described in the PEP that allows us to use those classes.

The main interface used by the rest of `pattern_matching` is match_args_and_kwargs.

If you want to add additional handlers for third party modules, or even the stdlib, you can call `register`/`regsiter_special`
"""
from __future__ import annotations

from dataclasses import is_dataclass, fields
from typing import Any, Tuple, Optional, Callable, TypeVar

special_attributes = {
    "<self>": lambda x: x
}

builtin_match_args = {
    list: ("<self>",), set: ("<self>",), dict: ("<self>",), frozenset: ("<self>",), tuple: ("<self>",),
    bool: ("<self>",), float: ("<self>",), int: ("<self>",), str: ("<self>",), bytes: ("<self>",),
    bytearray: ("<self>",),
}

special_handlers: list[tuple[Callable[[Any], bool], Callable[[Any], tuple[str, ...]]]] = []

def module_qualname(t: type) -> str:
    return f"{t.__module__}.{t.__qualname__}"

known_cases: dict[str, tuple[str,...]] = { # This helps to avoid importing modules that aren't actually used
}

def register(module_qualname: str, match_args: tuple[str, ...]):
    known_cases[module_qualname] = match_args

def register_special(checker: Callable[[Any], bool], match_args_gen: Callable[[Any], tuple[str, ...]]):
    """
    `checker` will be called for each type for which we don't have an override in `register`.
    Note that this is best for dynamic classes like `namedtuple`s. Note that neither `checker`
     nor `match_args_gen` have access to the instance
    """
    special_handlers.append((checker, match_args_gen))

def __match_args__(t):
    try:
        return t.__match_args__
    except AttributeError:
        if t in builtin_match_args:
            return builtin_match_args[t]
        qn = module_qualname(t)
        if qn in known_cases:
            return known_cases[qn]
        for ch, ma in special_handlers:
            if ch(t):
                return ma(t)
    return ()

T = TypeVar('T')

def match_args_and_kwargs(t, val: Any, args: Tuple[T, ...], kwargs: tuple[tuple[str, T], ...]) -> Optional[tuple[tuple[Any, T], ...]]:
    """
    Implements the algorithm described in PEP-634.
    """
    if len(args) == 0 and len(kwargs) == 0:
        return ()
    ma = __match_args__(t)
    assert isinstance(ma, (list, tuple)), ma
    if len(ma) < len(args):
        raise TypeError(f"Too many positional arguments for {type(val)} (expected at most {len(ma)}, got {len(args)})")
    taken = {n for n, _ in kwargs}
    named_args = []
    for n, a in zip(ma, args):
        if n in taken:
            raise TypeError(f"Duplicate keyword: {n}")
        taken.add(n)
        named_args.append((n, a))
    out = []
    for n, k in (named_args + list(kwargs)):
        if n in special_attributes:
            v = special_attributes[n](val)
        else:
            try:
                v = getattr(val, n)
            except AttributeError:
                return None
        out.append((k, v))
    return out




def _match_args_from_dataclass(t):
    return tuple(f.name for f in fields(t) if f.init)

def _is_namedtuple(obj):
    cls = obj if isinstance(obj, type) else type(obj)
    bases = cls.__bases__
    if bases != (tuple,): return False
    fields = getattr(obj, '_fields', None)
    if not isinstance(fields, tuple): return False
    return all(type(n) == str for n in fields)

def _match_args_from_namedtuple(t):
    return t._fields

register_special(is_dataclass, _match_args_from_dataclass)
register_special(_is_namedtuple, _match_args_from_namedtuple)

register('lark.tree.Tree', ('data', 'children'))
register('lark.lexer.Token', ('type', 'value'))