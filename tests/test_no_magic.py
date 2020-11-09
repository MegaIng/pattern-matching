from __future__ import annotations

import unittest
from unittest import TestCase

from lark import v_args

from pattern_matching.pattern_engine import pattern_lark_parser
from tests.examples import EXAMPLES, ExampleTranslator, Rebuild

from pattern_matching import Matcher

@v_args(inline=True)
class PEP634_To_NoMagic(Rebuild):
    def start(self, pat, guard):
        if guard is not None:
            return f"m.case({pat!r}) and {guard}"
        else:
            return f"m.case({pat!r})"

_to_no_magic = PEP634_To_NoMagic()

class _NoMagicTranslator(ExampleTranslator):
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        return f"with Matcher({', '.join(used_names)})({expr}) as m:\n"

    def case(self, pattern: str, is_first_case: bool) -> str:
        p = _to_no_magic.transform(pattern_lark_parser.parse(pattern))
        if is_first_case:
            return f"    if {p}:\n"
        else:
            return f"    elif {p}:\n"

    def bound_access(self, name: str) -> str:
        return f"m.{name}"

no_magic = _NoMagicTranslator()


class TestNoMagic(TestCase):
    def test_examples(self):
        for n, v in EXAMPLES.items():
            output = no_magic.run_example(v, {'Matcher': Matcher})
            self.assertEqual(v.output,output, msg=n)
            
if __name__ == '__main__':
    unittest.main()