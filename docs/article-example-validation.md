# Article Example Validation

Date: 2026-03-17

## Source Examples

- Hungarian example: the article's `10x10 min-cost perfect matching` matrix
- Hungarian expected cost: `206`
- Sudoku example: the article's published puzzle string
- Sudoku puzzle: `8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..`
- Sudoku expected checksum: `1276684605`

## Results

| Example | Mode | Success | Result | Expected | Steps | Elapsed | Transformer Subset | Notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| hungarian_10x10 | reference | yes | 206 | 206 | 17491 | 16.70 ms | yes | - |
| hungarian_10x10 | append_only_naive | yes | 206 | 206 | 17491 | 6.305 s | yes | - |
| hungarian_10x10 | append_only_hull | yes | 206 | 206 | 17491 | 485.46 ms | yes | - |
| hungarian_10x10 | transformer_hull | yes | 206 | 206 | 17491 | 1.729 s | yes | - |
| sudoku_checksum | reference | yes | 1276684605 | 1276684605 | 22370167 | 26.895 s | yes | - |

## Interpretation

- The Hungarian example is now validated end-to-end across the semantic reference, append-only naive timeline, append-only hull timeline, and tiny transformer-style hull path.
- The Sudoku example is validated against an independent checksum under the reference WASM executor and is now inside the current transformer opcode subset.
- The current repository does not run the full Sudoku trace through the append-only or transformer paths by default because the trace is much longer than the Hungarian example.

## Raw Results

```json
{
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
}
```
