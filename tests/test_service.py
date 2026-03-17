from __future__ import annotations

from base64 import b64encode
import shutil
import unittest

from llm_computer.protocol import ExecutionMode, ExecutionRequest, ExecutionResponse, SourceKind
from llm_computer.service import ExecutionService
from llm_computer.wasm import compile_wat


SUPPORTED_WAT = """
(module
  (func (export "main") (result i32)
    i32.const 5
    i32.const 7
    i32.add
  )
)
"""

UNSUPPORTED_WAT = """
(module
  (func (export "main") (result i32)
    i32.const 9
    return
  )
)
"""


@unittest.skipUnless(shutil.which("wat2wasm"), "wat2wasm is required for WASM example compilation")
class ExecutionProtocolTest(unittest.TestCase):
    def test_request_and_response_json_round_trip(self) -> None:
        request = ExecutionRequest(
            source_kind=SourceKind.WAT,
            source=SUPPORTED_WAT,
            mode=ExecutionMode.AUTO,
            trace_limit=3,
        )
        restored_request = ExecutionRequest.from_json(request.to_json())
        self.assertEqual(request, restored_request)

        response = ExecutionResponse(
            ok=True,
            mode_requested=ExecutionMode.AUTO,
            mode_used=ExecutionMode.TRANSFORMER_HULL,
            source_kind=SourceKind.WAT,
            export_name="main",
            results=[12],
        )
        restored_response = ExecutionResponse.from_json(response.to_json())
        self.assertEqual(response, restored_response)

    def test_auto_mode_prefers_transformer_when_supported(self) -> None:
        service = ExecutionService()
        response = service.execute(ExecutionRequest(source_kind=SourceKind.WAT, source=SUPPORTED_WAT))
        self.assertTrue(response.ok)
        self.assertEqual(ExecutionMode.TRANSFORMER_HULL, response.mode_used)
        self.assertTrue(response.transformer_subset)
        self.assertEqual([12], response.results)

    def test_auto_mode_falls_back_for_unsupported_program(self) -> None:
        service = ExecutionService()
        response = service.execute(ExecutionRequest(source_kind=SourceKind.WAT, source=UNSUPPORTED_WAT))
        self.assertTrue(response.ok)
        self.assertEqual(ExecutionMode.APPEND_ONLY_HULL, response.mode_used)
        self.assertFalse(response.transformer_subset)
        self.assertEqual([9], response.results)

    def test_explicit_transformer_mode_rejects_unsupported_program(self) -> None:
        service = ExecutionService()
        response = service.execute(
            ExecutionRequest(
                source_kind=SourceKind.WAT,
                source=UNSUPPORTED_WAT,
                mode=ExecutionMode.TRANSFORMER_HULL,
            )
        )
        self.assertFalse(response.ok)
        self.assertIn("outside the transformer verification subset", response.error or "")

    def test_base64_wasm_source_executes(self) -> None:
        wasm_base64 = b64encode(compile_wat(SUPPORTED_WAT)).decode("ascii")
        service = ExecutionService()
        response = service.execute(
            ExecutionRequest(
                source_kind=SourceKind.WASM_BASE64,
                source=wasm_base64,
                mode=ExecutionMode.REFERENCE,
            )
        )
        self.assertTrue(response.ok)
        self.assertEqual([12], response.results)


if __name__ == "__main__":
    unittest.main()
