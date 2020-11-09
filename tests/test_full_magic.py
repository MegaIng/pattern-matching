from __future__ import annotations

import unittest
from pathlib import Path
from textwrap import indent

from lark import v_args
from lark.visitors import Transformer

from tests.examples import EXAMPLES, ExampleTranslator
from pattern_matching.full_magic import match
from pattern_matching.pattern_engine import pattern_lark_parser


@v_args(inline=True)
class PEP634_TO_PY(Transformer):
    def __default__(self, data, children, meta):
        raise NotImplementedError((data, children))
    
    def _unchanged(self, t):
        return t.value
    
    number = capture = string = _unchanged
    
    def value(self, *a):
        return '.'.join(a)
    
    def star_pattern(self, n):
        return f"*{n}"
    
    def sequence(self, *c):
        return '['+ ', '.join(c) + ']'
    
    def keyw(self, n, v):
        return f"{n}={v}"
    
    def keyws(self, *a):
        return ', '.join(a)

    def arguments(self, *c):
        if len(c) == 2 and c[1] is None:
            c = c[:1]
        return ', '.join(c)

    def pos(self, *c):
        return ', '.join(c)

    def class_pattern(self, name, args):
        if args is None:
            return f"{name}()"
        else:
            return f"{name}({args})"
    
    def or_pattern(self, *args):
        return ' | '.join(args)
    
    def mapping_item(self, k, v):
        return f"{k}: {v}"

    def mapping(self, *c):
        return '{'+ ', '.join(c) + '}'
    
    def as_pattern(self, base, name):
        return f"({name} := ({base}))"
    
pep634_to_py = PEP634_TO_PY()

class _FullMagicTranslator(ExampleTranslator):
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        return f"with match({expr}):\n"
    
    def case(self, pattern: str, is_first_case: bool) -> str:
        pattern = pep634_to_py.transform(pattern_lark_parser.parse(pattern))
        if is_first_case:
            return f"    if c@ {pattern}:\n"
        else:
            return f"    elif c@ {pattern}:\n"

    def bound_access(self, name: str) -> str:
        return name

full_magic = _FullMagicTranslator()

GENERATED_MODULE_NAME = 'generated_test_full_magic'
GENERATED_FILE_NAME = Path(__file__).with_name(GENERATED_MODULE_NAME + '.py')

def _generate_tests():
    with open(GENERATED_FILE_NAME, 'w') as f:
        f.write('''\
""" Auto generated """
from pattern_matching.full_magic import match
from unittest import TestCase
from contextlib import contextmanager, redirect_stdout
from io import StringIO

class TestFullMagicGenerated(TestCase):
    @contextmanager
    def assertOutputs(self, expected: str):
        buf = StringIO()
        with redirect_stdout(buf):
            yield
        self.assertMultiLineEqual(expected, buf.getvalue())
''')
        for n, e in EXAMPLES.items():
            f.write(f'''
    def {n.lower()}(self):\n
        with self.assertOutputs({e.output!r}):
{indent(full_magic.translate(e), ' ' * 12)}
''')

_generate_tests()
TestFullMagicGenerated = __import__(GENERATED_MODULE_NAME).TestFullMagicGenerated

if __name__ == '__main__':
    unittest.main()