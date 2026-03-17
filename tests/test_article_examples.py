from __future__ import annotations

import shutil
import unittest

from llm_computer.article_examples import run_hungarian_validation
from llm_computer.examples import ARTICLE_HUNGARIAN_EXPECTED_COST, article_sudoku_module
from llm_computer.transformer import supports_transformer_verification


@unittest.skipUnless(shutil.which("clang"), "clang is required for the article C-to-WASM examples")
class ArticleExampleTest(unittest.TestCase):
    def test_hungarian_validation_succeeds_across_local_modes(self) -> None:
        results = run_hungarian_validation()

        self.assertEqual(
            ["reference", "append_only_naive", "append_only_hull", "transformer_hull"],
            [result.mode for result in results],
        )
        for result in results:
            self.assertTrue(result.success)
            self.assertEqual(ARTICLE_HUNGARIAN_EXPECTED_COST, result.result)

    def test_sudoku_example_is_inside_transformer_opcode_subset(self) -> None:
        function = article_sudoku_module().exported_function("sudoku_checksum")
        self.assertTrue(supports_transformer_verification(function))


if __name__ == "__main__":
    unittest.main()
