from __future__ import annotations

import shutil
import unittest

from llm_computer.examples import compiled_c_sum_module, factorial_module, memory_roundtrip_module, memory_sum_module, triangular_sum_module
from llm_computer.transformer import TinyExecutionTransformer, supports_transformer_verification
from llm_computer.executor import HullTimeline, NaiveTimeline
from llm_computer.wasm import ReferenceWasmExecutor


@unittest.skipUnless(shutil.which("wat2wasm"), "wat2wasm is required for WASM example compilation")
class TinyTransformerTest(unittest.TestCase):
    def assertMatchesReference(self, module, export_name: str = "main") -> None:
        function = module.exported_function(export_name)
        reference = ReferenceWasmExecutor(function).run()
        naive = TinyExecutionTransformer(function, NaiveTimeline).run()
        hull = TinyExecutionTransformer(function, HullTimeline).run()

        for candidate in (naive, hull):
            self.assertEqual(reference.results, candidate.results)
            self.assertEqual(reference.locals_, candidate.locals_)
            self.assertEqual(len(reference.trace), len(candidate.trace))
            self.assertEqual(
                [(entry.ip, entry.instruction, entry.stack_delta, entry.branch_taken) for entry in reference.trace],
                [(entry.ip, entry.instruction, entry.stack_delta, entry.branch_taken) for entry in candidate.trace],
            )

    def test_factorial_matches_reference(self) -> None:
        self.assertMatchesReference(factorial_module(7))

    def test_triangular_sum_matches_reference(self) -> None:
        self.assertMatchesReference(triangular_sum_module(50))

    def test_memory_roundtrip_matches_reference(self) -> None:
        self.assertMatchesReference(memory_roundtrip_module(123456789))

    def test_memory_sum_matches_reference(self) -> None:
        self.assertMatchesReference(memory_sum_module(50))

    @unittest.skipUnless(shutil.which("clang"), "clang is required for C-to-WASM compilation")
    def test_compiled_c_program_matches_reference(self) -> None:
        function = compiled_c_sum_module(10).exported_function("sum_to")
        self.assertTrue(supports_transformer_verification(function))
        self.assertMatchesReference(compiled_c_sum_module(10), export_name="sum_to")


if __name__ == "__main__":
    unittest.main()
