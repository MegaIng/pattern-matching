from __future__ import annotations

from dataclasses import is_dataclass, fields
from typing import Any, Tuple, Iterable, Optional
from collections import namedtuple

special_attributes = {
    "<self>": lambda x: x
}

builtin_match_args = {
    list: ("<self>",), set: ("<self>",), dict: ("<self>",), frozenset: ("<self>",), tuple: ("<self>",),
    bool: ("<self>",), float: ("<self>",), int: ("<self>",), str: ("<self>",), bytes: ("<self>",),
    bytearray: ("<self>",),
}

def _match_args_from_dataclass(t):
    return tuple(f.name for f in fields(t) if f.init)

def _is_namedtuple(obj):
    """Returns True if obj is a dataclass or an instance of a
    dataclass."""
    cls = obj if isinstance(obj, type) else type(obj)
    bases = cls.__bases__
    if bases != (tuple,): return False
    fields = getattr(obj, '_fields', None)
    if not isinstance(fields, tuple): return False
    return all(type(n) == str for n in fields)

def _match_args_from_namedtuple(t):
    return t._fields

def __match_args__(t):
    try:
        return t.__match_args__
    except AttributeError:
        if t in builtin_match_args:
            return builtin_match_args[t]
        if is_dataclass(t):
            return _match_args_from_dataclass(t)
        if _is_namedtuple(t):
            return _match_args_from_namedtuple(t)
    return ()


def match_args_and_kwargs(t, val: Any, args: Tuple[Any, ...], kwargs: tuple[tuple[str, Any], ...]) -> Optional[tuple[tuple[Any, Any], ...]]:
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
