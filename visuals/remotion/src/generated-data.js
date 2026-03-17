export const articleData = {
  "articleExamples": {
    "date": "2026-03-17",
    "hungarian_expected_cost": 206,
    "hungarian_matrix": [
      [
        61,
        58,
        35,
        86,
        32,
        39,
        41,
        27,
        21,
        42
      ],
      [
        59,
        77,
        97,
        99,
        78,
        21,
        89,
        72,
        35,
        63
      ],
      [
        88,
        85,
        37,
        57,
        59,
        97,
        37,
        29,
        69,
        94
      ],
      [
        32,
        82,
        53,
        20,
        77,
        96,
        21,
        70,
        50,
        61
      ],
      [
        15,
        44,
        81,
        10,
        64,
        36,
        56,
        78,
        20,
        69
      ],
      [
        76,
        35,
        87,
        69,
        16,
        55,
        26,
        37,
        30,
        66
      ],
      [
        86,
        32,
        74,
        94,
        32,
        14,
        24,
        12,
        31,
        70
      ],
      [
        97,
        63,
        20,
        64,
        90,
        21,
        28,
        49,
        89,
        10
      ],
      [
        58,
        52,
        27,
        76,
        61,
        35,
        17,
        91,
        37,
        66
      ],
      [
        42,
        79,
        61,
        26,
        55,
        98,
        70,
        17,
        26,
        86
      ]
    ],
    "results": [
      {
        "elapsed_s": 0.0166973750165198,
        "example_id": "hungarian_10x10",
        "expected": 206,
        "mode": "reference",
        "notes": null,
        "result": 206,
        "steps": 17491,
        "success": true,
        "transformer_subset": true
      },
      {
        "elapsed_s": 6.305026624992024,
        "example_id": "hungarian_10x10",
        "expected": 206,
        "mode": "append_only_naive",
        "notes": null,
        "result": 206,
        "steps": 17491,
        "success": true,
        "transformer_subset": true
      },
      {
        "elapsed_s": 0.4854648329783231,
        "example_id": "hungarian_10x10",
        "expected": 206,
        "mode": "append_only_hull",
        "notes": null,
        "result": 206,
        "steps": 17491,
        "success": true,
        "transformer_subset": true
      },
      {
        "elapsed_s": 1.7291006250015926,
        "example_id": "hungarian_10x10",
        "expected": 206,
        "mode": "transformer_hull",
        "notes": null,
        "result": 206,
        "steps": 17491,
        "success": true,
        "transformer_subset": true
      },
      {
        "elapsed_s": 26.895499582984485,
        "example_id": "sudoku_checksum",
        "expected": 1276684605,
        "mode": "reference",
        "notes": null,
        "result": 1276684605,
        "steps": 22370167,
        "success": true,
        "transformer_subset": true
      }
    ],
    "sudoku_expected_checksum": 1276684605,
    "sudoku_puzzle": "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4.."
  },
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
  ],
  "sudokuReport": {
    "checksum_result": {
      "elapsed_s": 28.032039415993495,
      "expected": 1276684605,
      "mode": "reference",
      "notes": null,
      "result": 1276684605,
      "snapshot": {
        "depth": 1,
        "ip": 617,
        "local_nonzero_count": 10,
        "locals_digest": "0x95b95115d8def3fa",
        "memory_digest": "0x3ed57b393568137a",
        "next_instruction": null,
        "nonzero_memory_bytes": 471,
        "results": [
          1276684605
        ],
        "stack_digest": "0xb5320a9bbfdaa792",
        "stack_top": [
          1276684605
        ]
      },
      "steps": 22370167,
      "success": true
    },
    "date": "2026-03-17",
    "prefix_budgets": [
      1000,
      10000,
      100000
    ],
    "prefix_results": [
      {
        "budget": 1000,
        "elapsed_s": 0.0009725829877424985,
        "finished": false,
        "matches_reference": true,
        "mode": "reference",
        "notes": null,
        "result": 3048,
        "snapshot": {
          "depth": 1,
          "ip": 39,
          "local_nonzero_count": 5,
          "locals_digest": "0x24702ce7ec5de6ee",
          "memory_digest": "0xc79a88ac44323de5",
          "next_instruction": "i32.const 1",
          "nonzero_memory_bytes": 288,
          "results": [
            3048
          ],
          "stack_digest": "0x0d78edc70fc2e035",
          "stack_top": [
            3048
          ]
        },
        "steps": 1000
      },
      {
        "budget": 1000,
        "elapsed_s": 0.023617250000825152,
        "finished": false,
        "matches_reference": true,
        "mode": "append_only_naive",
        "notes": null,
        "result": 3048,
        "snapshot": {
          "depth": 1,
          "ip": 39,
          "local_nonzero_count": 5,
          "locals_digest": "0x24702ce7ec5de6ee",
          "memory_digest": "0xc79a88ac44323de5",
          "next_instruction": "i32.const 1",
          "nonzero_memory_bytes": 288,
          "results": [
            3048
          ],
          "stack_digest": "0x0d78edc70fc2e035",
          "stack_top": [
            3048
          ]
        },
        "steps": 1000
      },
      {
        "budget": 1000,
        "elapsed_s": 0.015225208015181124,
        "finished": false,
        "matches_reference": true,
        "mode": "append_only_hull",
        "notes": null,
        "result": 3048,
        "snapshot": {
          "depth": 1,
          "ip": 39,
          "local_nonzero_count": 5,
          "locals_digest": "0x24702ce7ec5de6ee",
          "memory_digest": "0xc79a88ac44323de5",
          "next_instruction": "i32.const 1",
          "nonzero_memory_bytes": 288,
          "results": [
            3048
          ],
          "stack_digest": "0x0d78edc70fc2e035",
          "stack_top": [
            3048
          ]
        },
        "steps": 1000
      },
      {
        "budget": 1000,
        "elapsed_s": 0.16051083299680613,
        "finished": false,
        "matches_reference": true,
        "mode": "transformer_hull",
        "notes": null,
        "result": 3048,
        "snapshot": {
          "depth": 1,
          "ip": 39,
          "local_nonzero_count": 5,
          "locals_digest": "0x24702ce7ec5de6ee",
          "memory_digest": "0xc79a88ac44323de5",
          "next_instruction": "i32.const 1",
          "nonzero_memory_bytes": 288,
          "results": [
            3048
          ],
          "stack_digest": "0x0d78edc70fc2e035",
          "stack_top": [
            3048
          ]
        },
        "steps": 1000
      },
      {
        "budget": 10000,
        "elapsed_s": 0.0101032089733053,
        "finished": false,
        "matches_reference": true,
        "mode": "reference",
        "notes": null,
        "result": 2,
        "snapshot": {
          "depth": 1,
          "ip": 248,
          "local_nonzero_count": 10,
          "locals_digest": "0x7c4c93cdbbc10d18",
          "memory_digest": "0x8ca3f17a19579ee1",
          "next_instruction": "local.set 0",
          "nonzero_memory_bytes": 395,
          "results": [
            2
          ],
          "stack_digest": "0x7717980363c8e066",
          "stack_top": [
            2
          ]
        },
        "steps": 10000
      },
      {
        "budget": 10000,
        "elapsed_s": 2.185019291995559,
        "finished": false,
        "matches_reference": true,
        "mode": "append_only_naive",
        "notes": null,
        "result": 2,
        "snapshot": {
          "depth": 1,
          "ip": 248,
          "local_nonzero_count": 10,
          "locals_digest": "0x7c4c93cdbbc10d18",
          "memory_digest": "0x8ca3f17a19579ee1",
          "next_instruction": "local.set 0",
          "nonzero_memory_bytes": 395,
          "results": [
            2
          ],
          "stack_digest": "0x7717980363c8e066",
          "stack_top": [
            2
          ]
        },
        "steps": 10000
      },
      {
        "budget": 10000,
        "elapsed_s": 0.24569512499147095,
        "finished": false,
        "matches_reference": true,
        "mode": "append_only_hull",
        "notes": null,
        "result": 2,
        "snapshot": {
          "depth": 1,
          "ip": 248,
          "local_nonzero_count": 10,
          "locals_digest": "0x7c4c93cdbbc10d18",
          "memory_digest": "0x8ca3f17a19579ee1",
          "next_instruction": "local.set 0",
          "nonzero_memory_bytes": 395,
          "results": [
            2
          ],
          "stack_digest": "0x7717980363c8e066",
          "stack_top": [
            2
          ]
        },
        "steps": 10000
      },
      {
        "budget": 10000,
        "elapsed_s": 1.824778249982046,
        "finished": false,
        "matches_reference": true,
        "mode": "transformer_hull",
        "notes": null,
        "result": 2,
        "snapshot": {
          "depth": 1,
          "ip": 248,
          "local_nonzero_count": 10,
          "locals_digest": "0x7c4c93cdbbc10d18",
          "memory_digest": "0x8ca3f17a19579ee1",
          "next_instruction": "local.set 0",
          "nonzero_memory_bytes": 395,
          "results": [
            2
          ],
          "stack_digest": "0x7717980363c8e066",
          "stack_top": [
            2
          ]
        },
        "steps": 10000
      },
      {
        "budget": 100000,
        "elapsed_s": 0.10164400000940077,
        "finished": false,
        "matches_reference": true,
        "mode": "reference",
        "notes": null,
        "result": 4294967295,
        "snapshot": {
          "depth": 2,
          "ip": 241,
          "local_nonzero_count": 12,
          "locals_digest": "0x37724f6eece1f0f4",
          "memory_digest": "0x95b6b7e3ca9832ef",
          "next_instruction": "i32.xor",
          "nonzero_memory_bytes": 415,
          "results": [
            4294967295
          ],
          "stack_digest": "0x536b5e5845081111",
          "stack_top": [
            178,
            4294967295
          ]
        },
        "steps": 100000
      },
      {
        "budget": 100000,
        "elapsed_s": 3.7364886660070624,
        "finished": false,
        "matches_reference": true,
        "mode": "append_only_hull",
        "notes": null,
        "result": 4294967295,
        "snapshot": {
          "depth": 2,
          "ip": 241,
          "local_nonzero_count": 12,
          "locals_digest": "0x37724f6eece1f0f4",
          "memory_digest": "0x95b6b7e3ca9832ef",
          "next_instruction": "i32.xor",
          "nonzero_memory_bytes": 415,
          "results": [
            4294967295
          ],
          "stack_digest": "0x536b5e5845081111",
          "stack_top": [
            178,
            4294967295
          ]
        },
        "steps": 100000
      },
      {
        "budget": 100000,
        "elapsed_s": 20.440745166997658,
        "finished": false,
        "matches_reference": true,
        "mode": "transformer_hull",
        "notes": null,
        "result": 4294967295,
        "snapshot": {
          "depth": 2,
          "ip": 241,
          "local_nonzero_count": 12,
          "locals_digest": "0x37724f6eece1f0f4",
          "memory_digest": "0x95b6b7e3ca9832ef",
          "next_instruction": "i32.xor",
          "nonzero_memory_bytes": 415,
          "results": [
            4294967295
          ],
          "stack_digest": "0x536b5e5845081111",
          "stack_top": [
            178,
            4294967295
          ]
        },
        "steps": 100000
      }
    ],
    "sudoku_expected_checksum": 1276684605,
    "sudoku_puzzle": "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4.."
  }
};
