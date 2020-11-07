from __future__ import annotations

import unittest
from unittest import TestCase

from tests.examples import EXAMPLES, ExampleTranslator

from pattern_matching import Matcher

class _NoMagicTranslator(ExampleTranslator):
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        return f"with Matcher({', '.join(used_names)})({expr}) as m:\n"

    def case(self, pattern: str, is_first_case: bool) -> str:
        if is_first_case:
            return f"    if m.case({pattern!r}):\n"
        else:
            return f"    elif m.case({pattern!r}):\n"

    def bound_access(self, name: str) -> str:
        return f"m.{name}"

mo_magic = _NoMagicTranslator()

class TestNoMagic(TestCase):
    def test_examples(self):
        for n, v in EXAMPLES.items():
            output = mo_magic.run_example(v, {'Matcher': Matcher})
            self.assertEqual(v.output,output, msg=n)
            
if __name__ == '__main__':
    unittest.main()