from __future__ import annotations

import unittest
from unittest import TestCase

from tests.examples import EXAMPLES, ExampleTranslator
from pattern_matching.injecting import match, case


class _InjectingTranslatorWithM(ExampleTranslator):
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        return f"with match({expr}) as m:\n"
    
    def case(self, pattern: str, is_first_case: bool) -> str:
        if is_first_case:
            return f"    if m.case({pattern!r}):\n"
        else:
            return f"    elif m.case({pattern!r}):\n"

    def bound_access(self, name: str) -> str:
        return name

injecting_with_m = _InjectingTranslatorWithM()

class _InjectingTranslatorWithoutM(ExampleTranslator):
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        return f"with match({expr}):\n"
    
    def case(self, pattern: str, is_first_case: bool) -> str:
        if is_first_case:
            return f"    if case({pattern!r}):\n"
        else:
            return f"    elif case({pattern!r}):\n"

    def bound_access(self, name: str) -> str:
        return name

injecting_without_m = _InjectingTranslatorWithoutM()

class TestInjecting(TestCase):
    def test_examples_with_m(self):
        for n, v in EXAMPLES.items():
            output = injecting_with_m.run_example(v, {'match': match})
            self.assertEqual(v.output,output, msg=n)

    def test_examples_without_m(self):
        for n, v in EXAMPLES.items():
            output = injecting_without_m.run_example(v, {'match': match, 'case': case})
            self.assertEqual(v.output,output, msg=n)


if __name__ == '__main__':
    unittest.main()