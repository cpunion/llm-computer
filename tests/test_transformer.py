from __future__ import annotations

import shutil
import unittest

from llm_computer.examples import compiled_c_sum_module, factorial_module, memory_roundtrip_module, memory_sum_module, triangular_sum_module
from llm_computer.transformer import DecodedInstruction, TinyExecutionBlock, TinyExecutionTransformer, supports_transformer_verification
from llm_computer.executor import HullTimeline, NaiveTimeline
from llm_computer.wasm import ReferenceWasmExecutor, WasmOpcode


class FakeState:
    def __init__(
        self,
        *,
        stack: dict[int, int] | None = None,
        locals_: dict[int, int] | None = None,
        memory: dict[int, int] | None = None,
    ) -> None:
        self._stack = stack or {}
        self._locals = locals_ or {}
        self._memory = memory or {}

    def stack_read(self, slot: int, step: int) -> int:
        return self._stack.get(slot, 0)

    def local_read(self, index: int, step: int) -> int:
        return self._locals.get(index, 0)

    def memory_read_i32(self, address: int, step: int) -> int:
        value = 0
        for offset in range(4):
            value |= (self._memory.get(address + offset, 0) & 0xFF) << (offset * 8)
        return value


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

    def test_execution_block_exposes_feature_transition_writeback_stages(self) -> None:
        block = TinyExecutionBlock()
        state = FakeState(stack={0: 6, 1: 7})
        instruction = DecodedInstruction(opcode=WasmOpcode.I32_ADD)

        features = block.extract_features(instruction, ip=4, step=9, depth_before=2, state=state)
        signal = block.apply_transition(features)
        writes = block.plan_writeback(features, signal)

        self.assertEqual(7, features.top)
        self.assertEqual(6, features.second)
        self.assertEqual(5, signal.next_ip)
        self.assertEqual(1, signal.depth_after)
        self.assertEqual(13, signal.value)
        self.assertEqual([("stack", 0, 13)], [(write.target, write.index, write.value) for write in writes])

    def test_execution_block_plans_memory_store_writeback(self) -> None:
        block = TinyExecutionBlock()
        state = FakeState(stack={0: 16, 1: 0x11223344})
        instruction = DecodedInstruction(opcode=WasmOpcode.I32_STORE, memory_offset=4)

        features = block.extract_features(instruction, ip=7, step=3, depth_before=2, state=state)
        signal = block.apply_transition(features)
        writes = block.plan_writeback(features, signal)

        self.assertEqual(20, features.effective_address)
        self.assertEqual(0x11223344, signal.value)
        self.assertEqual(
            [
                ("memory", 20, 0x44),
                ("memory", 21, 0x33),
                ("memory", 22, 0x22),
                ("memory", 23, 0x11),
            ],
            [(write.target, write.index, write.value) for write in writes],
        )


if __name__ == "__main__":
    unittest.main()
