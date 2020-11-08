from __future__ import annotations

import unittest
from pathlib import Path
from textwrap import indent

from tests.examples import EXAMPLES, ExampleTranslator
from pattern_matching.full_magic import match


class _FullMagicTranslator(ExampleTranslator):
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        return f"with match({expr}):\n"
    
    def case(self, pattern: str, is_first_case: bool) -> str:
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
            if n == 'TEST_AS':
                continue
            f.write(f'''
    def {n.lower()}(self):\n
        with self.assertOutputs({e.output!r}):
{indent(full_magic.translate(e), ' ' * 12)}
''')

_generate_tests()
TestFullMagicGenerated = __import__(GENERATED_MODULE_NAME).TestFullMagicGenerated

if __name__ == '__main__':
    unittest.main()