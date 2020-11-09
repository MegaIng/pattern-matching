from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    name: str
    code: str
    output: str
    used_names: tuple[str, ...] = ()


TEST_LITERAL = Example('TEST_LITERAL', """
def http_error(status):
    match status:
        case 400:
            return "Bad request"
        case 404:
            return "Not found"
        case 418:
            return "I'm a teapot"
        case _:
            return "Something's wrong with the Internet"

print(http_error(200))
print(http_error(418))
""", """\
Something's wrong with the Internet
I'm a teapot
""")

TEST_ATTRIBUTE = Example('TEST_ATTRIBUTE', """
from enum import Enum
class Color(Enum):
    RED = 0
    GREEN = 1
    BLUE = 2
for color in (Color.BLUE, Color.RED):
    match color:
        case Color.RED:
            print("I see red!")
        case Color.GREEN:
            print("Grass is green")
        case Color.BLUE:
            print("I'm feeling the blues :(")
""", """\
I'm feeling the blues :(
I see red!
""", ("Color",))

TEST_TUPLE = Example('TEST_TUPLE', """
for point in ((0, 5), "Apple", (5, 5)):
    match point:
        case (0, 0):
            print("Origin")
        case (0, y):
            print(f"Y={$y}")
        case (x, 0):
            print(f"X={$x}")
        case (x, y):
            print(f"X={$x}, Y={$y}")
        case _:
            print(ValueError("Not a point"))
""", """\
Y=5
Not a point
X=5, Y=5
""")

TEST_CLASS = Example('TEST_CLASS', """
class Point:
    x: int
    y: int
    
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

def where_is(point):
    match point:
        case Point(x=0, y=0):
            print("Origin")
        case Point(x=0, y=y):
            print(f"Y={$y}")
        case Point(x=x, y=0):
            print(f"X={$x}")
        case Point():
            print("Somewhere else")
        case _:
            print("Not a point")
where_is(Point(5, 5))
where_is(5)
where_is(Point(0, 5))
where_is(Point(0, 0))
where_is(Point(5, 0))
""", """\
Somewhere else
Not a point
Y=5
Origin
X=5
""", ("Point", ))

TEST_CLASS_2 = Example('TEST_CLASS_2', """
class Point:
    x: int
    y: int
    
    __match_args__ = ('x', 'y')
    
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

def where_is(point):
    match point:
        case Point(0, 0):
            print("Origin")
        case Point(0, y):
            print(f"Y={$y}")
        case Point(x, 0):
            print(f"X={$x}")
        case Point():
            print("Somewhere else")
        case _:
            print("Not a point")
where_is(Point(5, 5))
where_is(5)
where_is(Point(0, 5))
where_is(Point(0, 0))
where_is(Point(5, 0))
""", """\
Somewhere else
Not a point
Y=5
Origin
X=5
""", ("Point", ))

TEST_STAR = Example('TEST_STAR', """
def sort(a):
    match a:
        case []:
            return []
        case [a]:
            return [$a]
        case [a, b]:
            return [$a, $b] if $a < $b else [$b, $a]
        case [a, *ele]:
            return sort([e for e in $ele if e < $a]) + [$a] + sort([e for e in $ele if e >= $a])
print(sort([1, 2, 3]))
print(sort([1, 3, 2]))
print(sort([4, 1, 3, 2]))
""", """\
[1, 2, 3]
[1, 2, 3]
[1, 2, 3, 4]
""")

TEST_OR = Example('TEST_OR', """
def do(command):
    match command.split():
        case ["north"] | ["go", "north"]:
            print("Going north")
        case ["get", obj] | ["pick", "up", obj] | ["pick", obj, "up"]:
            print("Grabbing", $obj)
        case _:
            print("Unknown command", command)

do("go south")
do("get paper")
do("pick up pencil")
do("north")
do("pick note up")
""", """\
Unknown command go south
Grabbing paper
Grabbing pencil
Going north
Grabbing note
""")

TEST_AS = Example('TEST_AS', """
def do(command):
    match command.split():
        case ["go", ("north" | "south" | "east" | "west") as direction]:
            print("Going", $direction)
        case _:
            print("Unknown command", command)
            
do("go south")
do("go south-west")
""", """\
Going south
Unknown command go south-west
""")

TEST_MAPPING = Example('TEST_MAPPING', """
actions = [
    {"text": "Hello World", "color": "blue"},
    {"sound": "hello_world.ogg", "format": "ogg"},
    {"sound": 5, "format": "ogg"},
    {"sound": "hello_world.ogg"},
    {"sound": "goodbye.wav", "format": "wav"},
]
for action in actions:
    match action:
        case {"text": message, "color": c}:
            print("Set output color", $c)
            print("Displaying", $message)
        case {"sleep": duration}:
            print("Waiting", $duration)
        case {"sound": url, "format": "ogg"}:
            print("Playing ogg sound", $url)
        case {"sound": _, "format": _}:
            print("Unsupported audio format")
        case _:
            print("Invalid action", action)

""", """\
Set output color blue
Displaying Hello World
Playing ogg sound hello_world.ogg
Playing ogg sound 5
Invalid action {'sound': 'hello_world.ogg'}
Unsupported audio format
""")

TEST_BUILTINS = Example('TEST_BUILTINS', """
actions = [
    {"text": "Hello World", "color": "blue"},
    {"sound": "hello_world.ogg", "format": "ogg"},
    {"sound": 5, "format": "ogg"},
    {"sound": "hello_world.ogg"},
    {"sleep": "50000"},
    {"sound": "goodbye.wav", "format": "wav"},
]
for action in actions:
    match action:
        case {"text": str(message), "color": str(c)}:
            print("Set output color", $c)
            print("Displaying", $message)
        case {"sleep": float(duration)}:
            print("Waiting", $duration)
        case {"sound": str(url), "format": "ogg"}:
            print("Playing ogg sound", $url)
        case {"sound": _, "format": _}:
            print("Unsupported audio format")
        case _:
            print("Invalid action", action)

""", """\
Set output color blue
Displaying Hello World
Playing ogg sound hello_world.ogg
Unsupported audio format
Invalid action {'sound': 'hello_world.ogg'}
Invalid action {'sleep': '50000'}
Unsupported audio format
""", ('str', 'float'))

TEST_FALLTHROUGH = Example('TEST_FALLTHROUGH', """
for i in range(1, 8):
    match i:
        case 1:
            print(1)
            continue
        case 2|3|4:
            print(2, 3, 4)
            continue
    print(">4")
""", """\
1
2 3 4
2 3 4
2 3 4
>4
>4
>4
""")

TEST_FALLTHROUGH_2 = Example('TEST_FALLTHROUGH_2', """
def classify(i):
    match i:
        case 1:
            print(1)
        case 2|3|4:
            print(2, 3, 4)

classify(1)
classify(2)
classify(4)
classify(8)
""", """\
1
2 3 4
2 3 4
""")

TEST_DATACLASS = Example('TEST_DATACLASS', """
from dataclasses import dataclass
from typing import Union

@dataclass
class Node:
    data: str
    children: list[Union[str, 'Node']]

@dataclass
class Leaf:
    data: int


def eval(n):
    match n:
        case Leaf(a):
            return $a
        case Node("+", [left, right]):
            return eval($left) + eval($right)

print(eval(Leaf(1)))
print(eval(Node('+', [Leaf(5), Leaf(6)])))
""", """\
1
11
""", ('Node', 'Leaf'))

TEST_NAMED_TUPLE = Example('TEST_NAMED_TUPLE', """
from collections import namedtuple
from typing import Union

Node = namedtuple('Node', 'data left right')

def eval(n):
    match n:
        case Node("+", left, right):
            return eval($left) + eval($right)
        case Node() as n:
            raise ValueError($n)
        case a:
            return $a

print(eval(1))
print(eval(Node('+', 5, 6)))
""", """\
1
11
""", ('Node',))

TEST_NAMED_TUPLE_2 = Example('TEST_NAMED_TUPLE_2', """
from typing import NamedTuple
from typing import Union

class Node(NamedTuple):
    data: str
    left: Union['Node', int]
    right: Union['Node', int]

def eval(n):
    match n:
        case Node("+", left, right):
            return eval($left) + eval($right)
        case Node() as n:
            raise ValueError($n)
        case a:
            return $a

print(eval(1))
print(eval(Node('+', 5, 6)))
""", """\
1
11
""", ('Node',))

TEST_LARK = Example('TEST_LARK', """
from lark import Tree, Token, Lark

parser = Lark('''
start: noun VERB noun
     | noun "is" ADJ

VERB: "is"|"has"|"hate"

noun: ADJ? NOUN+

ADJ: "great"|"bad"|"normal"
NOUN: "he"|"python"|"fruit"|"flies"
%ignore " "
''', parser='lalr', cache=True)

def analyse(sentence):
    match parser.parse(sentence).children:
        case Tree(children=[noun]), adj:
            print($adj, $noun)
        case Tree(children=[noun]), Token("VERB", verb), Tree('noun', [Token("ADJ") as adj, *nouns]):
            print($adj, $noun, *$nouns)
analyse("python is great")
analyse("flies hate normal fruit flies")
""", """\
great python
normal flies fruit flies
""", ('Tree', 'Token'))


EXAMPLES: dict[str, Example] = {k: v for k, v in locals().items() if isinstance(v, Example)}

_MATCH_PATTERN = re.compile("match (.*):\n")
_CASE_PATTERN  = re.compile("    case (.*):")
_BOUND_ACCESS_PATTERN = re.compile("\$(\w+)")
    

class ExampleTranslator(ABC):
    @abstractmethod
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        raise NotImplementedError

    @abstractmethod
    def case(self, pattern: str, is_first_case: bool) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def bound_access(self, name: str) -> str:
        raise NotImplementedError

    def translate(self, e: Example) -> str:
        code = _MATCH_PATTERN.sub(lambda m: self.match(m.group(1), e.used_names), e.code)

        is_first_case = True
        def _case(m):
            nonlocal is_first_case
            r = self.case(m.group(1), is_first_case)
            is_first_case = False
            return r
        code = _CASE_PATTERN.sub(_case, code)
        code = _BOUND_ACCESS_PATTERN.sub(lambda m: self.bound_access(m.group(1)), code)
        assert compile(code, "<example>", 'exec') is not None
        return code
    
    def run_example(self, e: Example, glbs: dict[str, Any]) -> str:
        code = self.translate(e)
        out = []
        def fake_print(*args, sep=" ", end="\n"):
            out.append(sep.join(map(str, args)) + end)
        try:
            exec(code, {**glbs, 'print': fake_print})
        except Exception:
            print(f"--- Generated code for failing example {e.name} (with {self.__class__.__name__}) ---", flush=True)
            print(code)
            print(f"------------------------------------------------------------------------------------")
            raise
        return ''.join(out)
