export const articleData = {
  "generated_on": "2026-03-17",
  "methods": [
    {
      "category": "direct",
      "comparison": {
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
      "depth_caption": "Pure semantic control with no model in the loop.",
      "depth_rank": 1,
      "execution_boundary": "The service calls the reference WASM executor directly.",
      "implementation_notes": [
        "Uses `ReferenceWasmExecutor` as the canonical semantics oracle.",
        "Bypasses prompt protocols, wrappers, and tool calls entirely.",
        "Defines the trace shape that every deeper implementation must preserve."
      ],
      "implementation_summary": "This is the cleanest semantic baseline: parse WASM, execute it with ordinary mutable state, and return the result without any model orchestration.",
      "method_id": "reference_direct",
      "short_label": "Reference",
      "testing_notes": [
        "Passed the five-way comparison scenario with final value `42`.",
        "Validated Hungarian end-to-end with result `206`.",
        "Validated the full article Sudoku checksum `1276684605` in `22,370,167` steps."
      ],
      "title": "Reference Direct",
      "validation_flags": {
        "article_hungarian": true,
        "native_block": false,
        "real_model": false,
        "structured_capture": false,
        "sudoku_full": true,
        "sudoku_prefix": true,
        "tool_call": false,
        "toy_scenario": true
      }
    },
    {
      "category": "direct",
      "comparison": {
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
      "depth_caption": "The article mechanism without model integration or geometric acceleration.",
      "depth_rank": 2,
      "execution_boundary": "The service calls the append-only executor with a naive timeline scan.",
      "implementation_notes": [
        "Replaces mutable locals and stack with append-only state timelines.",
        "Uses the same request/response boundary as other direct backends.",
        "Serves as the control for whether the hull trick actually matters."
      ],
      "implementation_summary": "This is the first mechanism-faithful executor: state is reconstructed from append-only writes, but retrieval still scans the whole history instead of using a hull-backed fast path.",
      "method_id": "append_only_naive_direct",
      "short_label": "Append-only Naive",
      "testing_notes": [
        "Passed the five-way comparison scenario with final value `42`.",
        "Validated Hungarian end-to-end with result `206`.",
        "Matched the reference Sudoku prefix state through `10,000` steps."
      ],
      "title": "Append-Only Naive Direct",
      "validation_flags": {
        "article_hungarian": true,
        "native_block": false,
        "real_model": false,
        "structured_capture": false,
        "sudoku_full": false,
        "sudoku_prefix": true,
        "tool_call": false,
        "toy_scenario": true
      }
    },
    {
      "category": "closed_source",
      "comparison": {
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
      },
      "depth_caption": "A hosted model delegates execution through a strict tool boundary.",
      "depth_rank": 3,
      "execution_boundary": "Gemini plans; the sidecar executes; Gemini narrates the final answer.",
      "implementation_notes": [
        "Uses `gemini-3-flash-preview` with forced tool use.",
        "Keeps the execution backend identical to the open-source path.",
        "Cannot move execution inside model weights because runtime internals are unavailable."
      ],
      "implementation_summary": "This is the best available path for closed-weight APIs: the model remains a planner, while the execution contract is enforced through a strict tool schema and the shared sidecar service.",
      "method_id": "closed_source_sidecar",
      "short_label": "Closed-source Sidecar",
      "testing_notes": [
        "Passed the five-way comparison scenario with final value `42`.",
        "Recorded `tool_calls=1` in live validation.",
        "Backed by dedicated Gemini integration tests plus the stage-3 and stage-10 validations."
      ],
      "title": "Closed-Source Sidecar",
      "validation_flags": {
        "article_hungarian": false,
        "native_block": false,
        "real_model": true,
        "structured_capture": false,
        "sudoku_full": false,
        "sudoku_prefix": false,
        "tool_call": true,
        "toy_scenario": true
      }
    },
    {
      "category": "open_source",
      "comparison": {
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
      "depth_caption": "An open-weight runtime intercepts execution requests at the prompt boundary.",
      "depth_rank": 4,
      "execution_boundary": "Qwen emits a structured execution request; the runtime resolves it and feeds back a response span.",
      "implementation_notes": [
        "Validated with `Qwen/Qwen2.5-0.5B-Instruct` through `Transformers`.",
        "Supports tagged requests, structured capture, and prefilled structured prompt mode.",
        "Still round-trips through runtime feedback rather than a native execution block."
      ],
      "implementation_summary": "This path keeps execution outside the model block graph, but it moves orchestration inside the open runtime: request extraction, structured capture, and response injection are all handled locally.",
      "method_id": "open_source_wrapper",
      "short_label": "Open-source Wrapper",
      "testing_notes": [
        "Passed the five-way comparison scenario with final value `42`.",
        "Recorded `intercepted_requests=1` and `structured_captures=1`.",
        "Covered by stages 4 through 8 plus the comparison harness."
      ],
      "title": "Open-Source Wrapper",
      "validation_flags": {
        "article_hungarian": false,
        "native_block": false,
        "real_model": true,
        "structured_capture": true,
        "sudoku_full": false,
        "sudoku_prefix": false,
        "tool_call": false,
        "toy_scenario": true
      }
    },
    {
      "category": "open_source",
      "comparison": {
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
      "depth_caption": "The closest current path to in-model execution without replacing real model weights.",
      "depth_rank": 5,
      "execution_boundary": "Qwen still emits the request, but the runtime resolves it natively and returns compact execution feedback instead of an `exec_response` text block.",
      "implementation_notes": [
        "Pins the backend to `transformer_hull` for the native execution round.",
        "Removes the `exec_response` text loop from the hot path.",
        "Acts as the bridge between today's wrapper integration and tomorrow's true in-model execution heads."
      ],
      "implementation_summary": "This is the deepest current integration: open-weight generation stays in the loop, yet the execution round-trip is resolved through a native execution-block path instead of a wrapper-only text protocol.",
      "method_id": "open_source_execution_block",
      "short_label": "Execution Block",
      "testing_notes": [
        "Passed the five-way comparison scenario with final value `42`.",
        "Recorded `native_execution_rounds=1` with no runtime answer fallback.",
        "Covered by stage 9, the comparison harness, and the transformer regression suite."
      ],
      "title": "Open-Source Execution Block",
      "validation_flags": {
        "article_hungarian": false,
        "native_block": true,
        "real_model": true,
        "structured_capture": true,
        "sudoku_full": false,
        "sudoku_prefix": false,
        "tool_call": false,
        "toy_scenario": true
      }
    }
  ]
};
