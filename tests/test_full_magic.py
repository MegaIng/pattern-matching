from __future__ import annotations

import unittest
from pathlib import Path
from textwrap import indent

from lark import v_args
from lark.visitors import Transformer

from tests.examples import EXAMPLES, ExampleTranslator, Rebuild
from pattern_matching.full_magic import match
from pattern_matching.pattern_engine import pattern_lark_parser


@v_args(inline=True)
class PEP634_TO_PY(Rebuild):
    def as_pattern(self, base, name):
        return f"({name} := ({base}))"
    
    def start(self, pat, guard):
        if guard is not None:
            return f"{pat} and {guard}"
        else:
            return pat

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
TestFullMagicGenerated = getattr(__import__('tests.' + GENERATED_MODULE_NAME), GENERATED_MODULE_NAME).TestFullMagicGenerated

if __name__ == '__main__':
    unittest.main()