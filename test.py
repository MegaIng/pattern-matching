from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union

from pattern_matching import Matcher

@dataclass
class Tree:
    data: str
    children: list[Union[Tree, str]]


match = Matcher(Tree)
with match(Tree('return', [Tree("number", [0])])) as m:
    if m.case('Tree("return", [])'):
        print("empty return")
    elif m.case('Tree("return", [Tree("var", [a])])'):
        print("return single var:", m.a)
    elif m.case('Tree("return", [a])'):
        print("return single expr:", m.a)
    elif m.case('Tree("return", [*a])'):
        print("return multiple values:", m.a)
    else:
        print(m.__value__)

with match({"a": 0, 1: "b"}) as m:
    if m.case('{"a": a, **kw}'):
        print(m.a, m.kw)
    if m.case('{}'):
        print(m.__value__)