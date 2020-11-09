from __future__ import annotations

import unittest
from unittest import TestCase

from lark import v_args

from pattern_matching.pattern_engine import pattern_lark_parser
from tests.examples import EXAMPLES, ExampleTranslator, Rebuild
from pattern_matching.injecting import match, case

@v_args(inline=True)
class PEP634_To_Injecting(Rebuild):
    def start(self, pat, guard):
        if guard is not None:
            return f"case({pat!r}) and {guard}"
        else:
            return f"case({pat!r})"

_to_injecting = PEP634_To_Injecting()

class _InjectingTranslatorWithM(ExampleTranslator):
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        return f"with match({expr}) as m:\n"
    
    def case(self, pattern: str, is_first_case: bool) -> str:
        p = _to_injecting.transform(pattern_lark_parser.parse(pattern))
        if is_first_case:
            return f"    if m.{p}:\n"
        else:
            return f"    elif m.{p}:\n"

    def bound_access(self, name: str) -> str:
        return name

injecting_with_m = _InjectingTranslatorWithM()

class _InjectingTranslatorWithoutM(ExampleTranslator):
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        return f"with match({expr}):\n"
    
    def case(self, pattern: str, is_first_case: bool) -> str:
        p = _to_injecting.transform(pattern_lark_parser.parse(pattern))
        if is_first_case:
            return f"    if {p}:\n"
        else:
            return f"    elif {p}:\n"

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