from __future__ import annotations

import unittest
from unittest import TestCase

from tests.examples import EXAMPLES, ExampleTranslator
from pattern_matching.injecting import match


class _InjectingTranslator(ExampleTranslator):
    def match(self, expr: str, used_names: tuple[str, ...]) -> str:
        return f"with match({expr}) as m:\n"
    
    def case(self, pattern: str, is_first_case: bool) -> str:
        if is_first_case:
            return f"    if m.case({pattern!r}):\n"
        else:
            return f"    elif m.case({pattern!r}):\n"

    def bound_access(self, name: str) -> str:
        return name

injecting = _InjectingTranslator()

class Injecting(TestCase):
    def test_examples(self):
        for n, v in EXAMPLES.items():
            output = injecting.run_example(v, {'match': match})
            self.assertEqual(v.output,output, msg=n)


if __name__ == '__main__':
    unittest.main()