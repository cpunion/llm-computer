# Sudoku Result Validation

Date: 2026-03-17

## Source Example

- Source: the article's published Sudoku puzzle
- Puzzle: `8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..`
- Expected checksum: `1276684605`

## Full Checksum Validation

| Mode | Success | Result | Expected | Steps | Elapsed | IP | Depth | Memory Bytes | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| reference | yes | 1276684605 | 1276684605 | 22370167 | 28.032 s | 617 | 1 | 471 | - |

## Prefix-State Validation

| Budget | Mode | Matches Reference | Finished | Result | Steps | Elapsed | IP | Depth | Stack Digest | Memory Digest | Notes |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 1000 | reference | yes | no | 3048 | 1000 | 0.97 ms | 39 | 1 | 0x0d78edc70fc2e035 | 0xc79a88ac44323de5 | - |
| 1000 | append_only_naive | yes | no | 3048 | 1000 | 23.62 ms | 39 | 1 | 0x0d78edc70fc2e035 | 0xc79a88ac44323de5 | - |
| 1000 | append_only_hull | yes | no | 3048 | 1000 | 15.23 ms | 39 | 1 | 0x0d78edc70fc2e035 | 0xc79a88ac44323de5 | - |
| 1000 | transformer_hull | yes | no | 3048 | 1000 | 160.51 ms | 39 | 1 | 0x0d78edc70fc2e035 | 0xc79a88ac44323de5 | - |
| 10000 | reference | yes | no | 2 | 10000 | 10.10 ms | 248 | 1 | 0x7717980363c8e066 | 0x8ca3f17a19579ee1 | - |
| 10000 | append_only_naive | yes | no | 2 | 10000 | 2.185 s | 248 | 1 | 0x7717980363c8e066 | 0x8ca3f17a19579ee1 | - |
| 10000 | append_only_hull | yes | no | 2 | 10000 | 245.70 ms | 248 | 1 | 0x7717980363c8e066 | 0x8ca3f17a19579ee1 | - |
| 10000 | transformer_hull | yes | no | 2 | 10000 | 1.825 s | 248 | 1 | 0x7717980363c8e066 | 0x8ca3f17a19579ee1 | - |
| 100000 | reference | yes | no | 4294967295 | 100000 | 101.64 ms | 241 | 2 | 0x536b5e5845081111 | 0x95b6b7e3ca9832ef | - |
| 100000 | append_only_hull | yes | no | 4294967295 | 100000 | 3.736 s | 241 | 2 | 0x536b5e5845081111 | 0x95b6b7e3ca9832ef | - |
| 100000 | transformer_hull | yes | no | 4294967295 | 100000 | 20.441 s | 241 | 2 | 0x536b5e5845081111 | 0x95b6b7e3ca9832ef | - |

## Interpretation

- The full Sudoku checksum is validated under the reference WASM executor.
- Prefix-state validation compares exact execution snapshots against the reference path at fixed step budgets.
- By default, `append_only_naive` is capped at `10,000` steps because it becomes disproportionately expensive on this trace, while `append_only_hull` and `transformer_hull` are validated through `100,000` steps.

## Raw Results

```json
{
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
```
