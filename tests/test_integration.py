from __future__ import annotations

import shutil
import unittest

from llm_computer.integration import ClosedSourceToolAdapter, OpenSourceRuntimeAdapter
from llm_computer.protocol import ExecutionMode, ExecutionRequest, ExecutionResponse, SourceKind


SUPPORTED_WAT = """
(module
  (func (export "main") (result i32)
    i32.const 2
    i32.const 3
    i32.mul
  )
)
"""


@unittest.skipUnless(shutil.which("wat2wasm"), "wat2wasm is required for WASM example compilation")
class IntegrationPrototypeTest(unittest.TestCase):
    def test_open_source_runtime_adapter_resolves_tagged_request(self) -> None:
        adapter = OpenSourceRuntimeAdapter()
        request = ExecutionRequest(
            source_kind=SourceKind.WAT,
            source=SUPPORTED_WAT,
            mode=ExecutionMode.AUTO,
            trace_limit=2,
        )
        text = "planner preface " + OpenSourceRuntimeAdapter.render_request_segment(request) + " planner suffix"
        response_segment = adapter.maybe_resolve(text)
        self.assertIn("<exec_response>", response_segment)
        response_json = (
            response_segment
            .split("<exec_response>", maxsplit=1)[1]
            .split("</exec_response>", maxsplit=1)[0]
        )
        response = ExecutionResponse.from_json(response_json)
        self.assertTrue(response.ok)
        self.assertEqual([6], response.results)

    def test_closed_source_tool_adapter_invokes_shared_schema(self) -> None:
        adapter = ClosedSourceToolAdapter()
        tool_spec = adapter.tool_spec()
        self.assertEqual("run_llm_computer", tool_spec["function"]["name"])

        response_dict = adapter.invoke_dict(
            {
                "source_kind": "wat",
                "source": SUPPORTED_WAT,
                "mode": "reference",
                "trace_limit": 1,
            }
        )
        self.assertTrue(response_dict["ok"])
        self.assertEqual([6], response_dict["results"])

    def test_request_schema_is_embedded_in_tool_spec(self) -> None:
        parameters = ClosedSourceToolAdapter.tool_spec()["function"]["parameters"]
        self.assertEqual("object", parameters["type"])
        self.assertIn("source_kind", parameters["required"])
        self.assertIn("source", parameters["required"])
        self.assertEqual(
            sorted([mode.value for mode in ExecutionMode]),
            sorted(parameters["properties"]["mode"]["enum"]),
        )


if __name__ == "__main__":
    unittest.main()
