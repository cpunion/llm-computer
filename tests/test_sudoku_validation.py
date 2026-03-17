from __future__ import annotations

import shutil
import unittest

from llm_computer.sudoku_validation import (
    SudokuChecksumValidation,
    SudokuPrefixValidationRow,
    SudokuStateDigest,
    render_markdown_report,
    run_sudoku_prefix_validation,
)


@unittest.skipUnless(shutil.which("clang"), "clang is required for the article C-to-WASM examples")
class SudokuValidationTest(unittest.TestCase):
    def test_prefix_validation_matches_reference_for_small_budget(self) -> None:
        rows = run_sudoku_prefix_validation(
            budgets=(1_000,),
            max_budget_by_mode={
                "append_only_naive": 1_000,
                "append_only_hull": 1_000,
                "transformer_hull": 1_000,
            },
        )

        self.assertEqual(
            ["reference", "append_only_naive", "append_only_hull", "transformer_hull"],
            [row.mode for row in rows],
        )
        for row in rows:
            self.assertTrue(row.matches_reference)

    def test_render_markdown_report_includes_prefix_section(self) -> None:
        snapshot = SudokuStateDigest(
            ip=12,
            next_instruction="local.get 0",
            depth=2,
            results=[],
            locals_digest="0x1",
            local_nonzero_count=1,
            stack_digest="0x2",
            stack_top=[3, 4],
            memory_digest="0x3",
            nonzero_memory_bytes=16,
        )
        checksum = SudokuChecksumValidation(
            mode="reference",
            success=True,
            result=123,
            expected=123,
            steps=456,
            elapsed_s=0.5,
            snapshot=snapshot,
        )
        prefix_rows = [
            SudokuPrefixValidationRow(
                budget=1_000,
                mode="reference",
                matches_reference=True,
                steps=1_000,
                elapsed_s=0.01,
                finished=False,
                result=None,
                snapshot=snapshot,
            )
        ]

        report = render_markdown_report(checksum, prefix_rows)

        self.assertIn("# Sudoku Result Validation", report)
        self.assertIn("## Prefix-State Validation", report)
        self.assertIn("| 1000 | reference | yes | no | - | 1000 | 10.00 ms |", report)


if __name__ == "__main__":
    unittest.main()
