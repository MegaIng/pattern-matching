from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from withhacks import WithHack
from pattern_matching import match, case


@dataclass
class Quoted:
    arg1: Any
    arg2: Any = None

@dataclass
class Name:
    name: str

@dataclass
class String:
    s: str


A = "Another String"

with match("se"):
    if case('Quoted(Name(name))'):
        print(1, name)
    elif case('Quoted(Name(name), String(value))'):
        print(2, name, value)
    elif case('Quoted(something_else)'):
        print(3, something_else)
    else:
        print(4)