# Benchmark Results

Date: 2026-03-17

Commands:

```bash
PYTHONPATH=src python3 -m llm_computer
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## What was measured

This repository reports three separate benchmarks:

1. Static support-point lookup over a fixed cache.
2. Online append-only query-plus-insert lookup.
3. End-to-end append-only program execution where `ip`, locals, and stack
   values are recovered from timelines instead of mutable machine state.
4. A memory-backed WASM example where linear memory is recovered from byte-level
   append-only writes.
5. A compiled C example that goes through `clang -> wasm32 -> parser ->
   append-only execution`.
6. A tiny transformer-style verification path for the restricted control-flow
   subset.

## Correctness checks

The append-only WASM executor matches the reference interpreter on the current
WASM example modules:

- `factorial_module(7)`: results match, trace length match.
- `triangular_sum_module(200)`: results match, trace length match.
- `memory_sum_module(200)`: results match, trace length match.
- `compiled_c_sum_module(10)`: results match, trace length match.
- `factorial_module(7)`, `triangular_sum_module(200)`, `memory_sum_module(200)`,
  and `compiled_c_sum_module(10)` also match under the transformer-style
  verifier.

The test suite also checks that the hull-backed timeline returns the same latest
write as the naive linear scan timeline.

## Measured results

Program execution:

| Program | Online hull | Naive scan | Speedup |
| --- | ---: | ---: | ---: |
| `factorial_module(7)` | `0.905 ms` | `0.438 ms` | `0.48x` |
| `triangular_sum_module(200)` | `51.300 ms` | `169.968 ms` | `3.31x` |
| `memory_sum_module(200)` | `64.553 ms` | `224.843 ms` | `3.48x` |
| `compiled_c_sum_module(10)` | `1.559 ms` | `0.762 ms` | `0.49x` |

Transformer-style verification:

| Program | Transformer hull | Transformer naive | Speedup |
| --- | ---: | ---: | ---: |
| `factorial_module(7)` | `1.900 ms` | `1.442 ms` | `0.76x` |
| `triangular_sum_module(200)` | `75.815 ms` | `193.824 ms` | `2.56x` |
| `memory_sum_module(200)` | `98.297 ms` | `254.496 ms` | `2.59x` |
| `compiled_c_sum_module(10)` | `2.984 ms` | `2.203 ms` | `0.74x` |

Static lookup benchmark:

| Trace length | Hull lookup | Naive scan | Speedup |
| --- | ---: | ---: | ---: |
| `100` | `1.636 us` | `4.630 us` | `2.83x` |
| `500` | `2.699 us` | `22.026 us` | `8.16x` |
| `1,000` | `3.700 us` | `44.935 us` | `12.14x` |
| `5,000` | `10.770 us` | `215.420 us` | `20.00x` |

Online append-only lookup benchmark:

| Trace length | Online hull | Naive scan | Speedup |
| --- | ---: | ---: | ---: |
| `100` | `0.581 ms` | `0.255 ms` | `0.44x` |
| `500` | `3.966 ms` | `5.655 ms` | `1.43x` |
| `1,000` | `9.623 ms` | `22.349 ms` | `2.32x` |
| `5,000` | `66.904 ms` | `542.475 ms` | `8.11x` |

## Interpretation

The current implementation supports the article's qualitative claim that:

- static geometric lookup can be much cheaper than scanning the full prefix,
- append-only online decoding only pays off after the trace is long enough,
- the same lookup mechanism can back actual execution rather than a synthetic
  microbenchmark,
- sparse linear memory can also be recovered from append-only writes, not just
  locals and stack slots,
- cumulative state such as stack depth can be reconstructed from append-only
  deltas rather than a separate mutable depth variable,
- the current subset is enough to execute at least one real `clang -> wasm32`
  compiled example rather than only hand-written WAT,
- a tiny transformer-style verifier can match the reference execution trace on a
  restricted subset without falling back to the general append-only executor,
- the transformer-style subset now includes linear memory and one compiled-C
  example rather than only stack-and-local toy programs.

It does not yet reproduce the full article system. Important missing pieces are:

- broad support for arbitrary C or C++ compiled WASM,
- compilation from C or WASM into model weights,
- a transformer that performs the execution directly for the full supported WASM
  surface without the current hand-written transition block,
- the article's published throughput numbers.
