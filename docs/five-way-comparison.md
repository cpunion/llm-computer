# Five-Way Comparison

Date: 2026-03-17

## Scenario

- WAT module: `(module (func (export "main") (result i32) i32.const 6 i32.const 7 i32.mul))`
- Expected final value: `42`
- Comparison set: semantic control, naive direct baseline, open-source wrapper, open-source execution block, closed-source sidecar

## Environment

- Open-source model: `Qwen/Qwen2.5-0.5B-Instruct`
- Closed-source model: `gemini-3-flash-preview`
- Open-source device: `mps`

## Results

| Method | Category | Success | Final Text | Used Execution | End-to-End | Backend | Backend Elapsed | Steps | Intercepted | Structured | Native Rounds | Tool Calls | Notes |
| --- | --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| reference_direct | direct | yes | `42` | yes | 30.85 ms | reference | 0.03 ms | 4 | - | - | - | - | direct service execution |
| append_only_naive_direct | direct | yes | `42` | yes | 17.52 ms | append_only_naive | 0.05 ms | 4 | - | - | - | - | direct service execution |
| open_source_wrapper | open_source | yes | `42` | yes | 1.178 s | transformer_hull | 0.14 ms | 4 | 1 | 1 | 0 | - | wrapper + structured + prefilled prefix |
| open_source_execution_block | open_source | yes | `42` | yes | 857.05 ms | transformer_hull | 0.13 ms | 4 | 1 | 1 | 1 | - | native execution-block + pinned transformer_hull backend |
| closed_source_sidecar | closed_source | yes | `42` | yes | 4.115 s | - | - | - | - | - | - | 1 | Gemini tool-calling via gemini-3-flash-preview |

## Interpretation

- Successful paths: `5/5`
- Fastest successful path in this run: `append_only_naive_direct` at 17.52 ms
- `reference_direct` is the semantic control and does not include any model orchestration overhead.
- `append_only_naive_direct` is the direct naive baseline for the article-style append-only execution path.
- `open_source_wrapper` and `open_source_execution_block` share the same Qwen-family runtime and request extraction logic; the difference is whether execution returns through `<exec_response>` text or through native execution feedback.
- `closed_source_sidecar` uses hosted Gemini tool-calling and is not directly latency-comparable to local open-source runs.

## Raw Results

```json
{
  "date": "2026-03-17",
  "environment": {
    "closed_source_model": "gemini-3-flash-preview",
    "device": "mps",
    "open_source_model": "Qwen/Qwen2.5-0.5B-Instruct"
  },
  "results": [
    {
      "backend_elapsed_s": 2.8207985451444983e-05,
      "backend_mode": "reference",
      "category": "direct",
      "end_to_end_s": 0.030849083996145055,
      "final_text": "42",
      "final_value": 42,
      "intercepted_requests": null,
      "method_id": "reference_direct",
      "native_execution_rounds": null,
      "notes": "direct service execution",
      "runtime_answer_fallbacks": null,
      "steps": 4,
      "structured_captures": null,
      "success": true,
      "tool_calls": null,
      "used_execution": true
    },
    {
      "backend_elapsed_s": 5.4292002459988e-05,
      "backend_mode": "append_only_naive",
      "category": "direct",
      "end_to_end_s": 0.01751516599324532,
      "final_text": "42",
      "final_value": 42,
      "intercepted_requests": null,
      "method_id": "append_only_naive_direct",
      "native_execution_rounds": null,
      "notes": "direct service execution",
      "runtime_answer_fallbacks": null,
      "steps": 4,
      "structured_captures": null,
      "success": true,
      "tool_calls": null,
      "used_execution": true
    },
    {
      "backend_elapsed_s": 0.00013666599988937378,
      "backend_mode": "transformer_hull",
      "category": "open_source",
      "end_to_end_s": 1.1775815839937422,
      "final_text": "42",
      "final_value": 42,
      "intercepted_requests": 1,
      "method_id": "open_source_wrapper",
      "native_execution_rounds": 0,
      "notes": "wrapper + structured + prefilled prefix",
      "runtime_answer_fallbacks": 0,
      "steps": 4,
      "structured_captures": 1,
      "success": true,
      "tool_calls": null,
      "used_execution": true
    },
    {
      "backend_elapsed_s": 0.00012745801359415054,
      "backend_mode": "transformer_hull",
      "category": "open_source",
      "end_to_end_s": 0.857051083992701,
      "final_text": "42",
      "final_value": 42,
      "intercepted_requests": 1,
      "method_id": "open_source_execution_block",
      "native_execution_rounds": 1,
      "notes": "native execution-block + pinned transformer_hull backend",
      "runtime_answer_fallbacks": 0,
      "steps": 4,
      "structured_captures": 1,
      "success": true,
      "tool_calls": null,
      "used_execution": true
    },
    {
      "backend_elapsed_s": null,
      "backend_mode": null,
      "category": "closed_source",
      "end_to_end_s": 4.114845749980304,
      "final_text": "42",
      "final_value": 42,
      "intercepted_requests": null,
      "method_id": "closed_source_sidecar",
      "native_execution_rounds": null,
      "notes": "Gemini tool-calling via gemini-3-flash-preview",
      "runtime_answer_fallbacks": null,
      "steps": null,
      "structured_captures": null,
      "success": true,
      "tool_calls": 1,
      "used_execution": true
    }
  ],
  "scenario": {
    "expected_final_value": 42,
    "wat_module": "(module (func (export \"main\") (result i32) i32.const 6 i32.const 7 i32.mul))"
  }
}
```
