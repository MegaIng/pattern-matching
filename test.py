from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from not_evil import Matcher


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

match = Matcher(Quoted, Name, String, A='Another String')

m = match(Quoted(Name("na")))
if m.case('Quoted(Name(name))'):
    print(1, m.name)
elif m.case('Quoted(Name(name), String(value))'):
    print(2, m.name, m.value)
elif m.case('Quoted(something_else)'):
    print(3, m.something_else)
elif m.case('A'):
    print(4)
else:
    print(5)