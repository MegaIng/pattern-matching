# from __future__ import annotations
# 
# from dataclasses import dataclass
# from typing import Any, Union
# 
# from pattern_matching.full_magic import match
# 
# @dataclass
# class Tree:
#     data: str
#     children: list[Union[Tree, str]]
# 
# 
# with match(Tree('return', [Tree("number", [0])])):
#     if Tree("return", []):
#         print("empty return")
#     elif Tree("return", [Tree("var", [a])]):
#         print("return single var:", a)
#     elif Tree("return", [a]):
#         print("return single expr:", a)
#     elif Tree("return", [*a]):
#         print("return multiple values:", a)
#     else:
#         pass
# 
# with match({"a": 0, 1: "b"}):
#     if {"a": a, **kw}:
#         print(m.a, m.kw)
#     elif {}:
#         print(m.__value__)
from pattern_matching.injecting import match


class Point:
    x: int
    y: int

    __match_args__ = ('x', 'y')

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


def where_is(point):
    y=x=5
    with match(point) as m:
        if m.case('Point(x=0, y=0)'):

            print("Origin")
        elif m.case('Point(x=0, y=y)'):
            print(locals())
            print(f"Y={y}")
        elif m.case('Point(x=x, y=0)'):

            print(f"X={x}")
        elif m.case('Point()'):

            print("Somewhere else")
        elif m.case('_'):

            print("Not a point")


where_is(Point(5, 5))
where_is(5)
where_is(Point(0, 5))
where_is(Point(0, 0))
where_is(Point(5, 0))