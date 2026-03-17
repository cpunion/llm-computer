from __future__ import annotations

import shutil
import unittest

from llm_computer.examples import (
    add_module,
    compiled_c_sum_module,
    factorial_module,
    memory_roundtrip_module,
    memory_sum_module,
    triangular_sum_module,
)
from llm_computer.executor import AppendOnlyWasmExecutor, HullTimeline, NaiveTimeline
from llm_computer.wasm import ReferenceWasmExecutor


@unittest.skipUnless(shutil.which("wat2wasm"), "wat2wasm is required for WASM example compilation")
class TimelineTest(unittest.TestCase):
    def test_hull_timeline_matches_naive_latest_write(self) -> None:
        naive = NaiveTimeline()
        hull = HullTimeline()
        values = [7, 11, 19, 23, 29, 31]

        for step, value in enumerate(values):
            self.assertEqual(naive.query(step), hull.query(step))
            naive.insert(step, value)
            hull.insert(step, value)

        for step in range(len(values), len(values) + 5):
            self.assertEqual(naive.query(step), hull.query(step))
            self.assertEqual(values[-1], hull.query(step))


@unittest.skipUnless(shutil.which("wat2wasm"), "wat2wasm is required for WASM example compilation")
class AppendOnlyExecutorTest(unittest.TestCase):
    def assertMatchesReference(self, module, export_name: str = "main") -> None:
        function = module.exported_function(export_name)
        reference = ReferenceWasmExecutor(function).run()
        naive = AppendOnlyWasmExecutor(function, NaiveTimeline).run()
        hull = AppendOnlyWasmExecutor(function, HullTimeline).run()

        for candidate in (naive, hull):
            self.assertEqual(reference.results, candidate.results)
            self.assertEqual(reference.locals_, candidate.locals_)
            self.assertEqual(len(reference.trace), len(candidate.trace))
            self.assertEqual(
                [(entry.ip, entry.instruction, entry.stack_delta, entry.branch_taken) for entry in reference.trace],
                [(entry.ip, entry.instruction, entry.stack_delta, entry.branch_taken) for entry in candidate.trace],
            )

    def test_add_module_matches_reference(self) -> None:
        self.assertMatchesReference(add_module(3, 5))

    def test_factorial_module_matches_reference(self) -> None:
        self.assertMatchesReference(factorial_module(7))

    def test_triangular_sum_module_matches_reference(self) -> None:
        self.assertMatchesReference(triangular_sum_module(50))

    def test_memory_roundtrip_module_matches_reference(self) -> None:
        self.assertMatchesReference(memory_roundtrip_module(123456789))

    def test_memory_sum_module_matches_reference(self) -> None:
        self.assertMatchesReference(memory_sum_module(50))

    @unittest.skipUnless(shutil.which("clang"), "clang is required for C-to-WASM compilation")
    def test_compiled_c_sum_module_matches_reference(self) -> None:
        self.assertMatchesReference(compiled_c_sum_module(10), export_name="sum_to")


if __name__ == "__main__":
    unittest.main()
