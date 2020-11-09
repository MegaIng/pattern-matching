from __future__ import annotations

import unittest
from unittest import TestCase

from lark import v_args

from pattern_matching.pattern_engine import pattern_lark_parser
from tests.examples import EXAMPLES, ExampleTranslator, Rebuild
from pattern_matching.auto_lookup import match


@v_args(inline=True)
class PEP634_To_AutoLookup(Rebuild):
    def start(self, pat, guard):
        if guard is not None:
            return f"m.case({pat!r}) and {guard}"
        else:
            return f"m.case({pat!r})"


_to_auto_lookup = PEP634_To_AutoLookup()


class _AutoLookupTranslator(ExampleTranslator):
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        return f"with match({expr}) as m:\n"

    def case(self, pattern: str, is_first_case: bool) -> str:
        p = _to_auto_lookup.transform(pattern_lark_parser.parse(pattern))
        if is_first_case:
            return f"    if {p}:\n"
        else:
            return f"    elif {p}:\n"

    def bound_access(self, name: str) -> str:
        return f"m.{name}"

auto_lookup = _AutoLookupTranslator()

class TestAutoLookup(TestCase):
    def test_examples(self):
        for n, v in EXAMPLES.items():
            output = auto_lookup.run_example(v, {'match': match})
            self.assertEqual(v.output,output, msg=n)


if __name__ == '__main__':
    unittest.main()