# Benchmark Results

Date: 2026-03-17

Commands:

```bash
PYTHONPATH=src python3 -m llm_computer
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## What was measured

All numbers below come from one representative local run of
`PYTHONPATH=src python3 -m llm_computer`. They will vary slightly across
machines and repeated runs.

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
| `factorial_module(7)` | `0.910 ms` | `0.437 ms` | `0.48x` |
| `triangular_sum_module(200)` | `51.163 ms` | `171.338 ms` | `3.35x` |
| `memory_sum_module(200)` | `63.983 ms` | `226.393 ms` | `3.54x` |
| `compiled_c_sum_module(10)` | `1.624 ms` | `0.747 ms` | `0.46x` |

Transformer-style verification:

| Program | Transformer hull | Transformer naive | Speedup |
| --- | ---: | ---: | ---: |
| `factorial_module(7)` | `2.032 ms` | `1.475 ms` | `0.73x` |
| `triangular_sum_module(200)` | `75.667 ms` | `190.954 ms` | `2.52x` |
| `memory_sum_module(200)` | `97.251 ms` | `250.459 ms` | `2.58x` |
| `compiled_c_sum_module(10)` | `2.888 ms` | `2.157 ms` | `0.75x` |

Static lookup benchmark:

| Trace length | Hull lookup | Naive scan | Speedup |
| --- | ---: | ---: | ---: |
| `100` | `1.613 us` | `4.473 us` | `2.77x` |
| `500` | `2.665 us` | `21.772 us` | `8.17x` |
| `1,000` | `3.592 us` | `44.021 us` | `12.26x` |
| `5,000` | `10.463 us` | `214.213 us` | `20.47x` |

Online append-only lookup benchmark:

| Trace length | Online hull | Naive scan | Speedup |
| --- | ---: | ---: | ---: |
| `100` | `0.554 ms` | `0.255 ms` | `0.46x` |
| `500` | `3.871 ms` | `5.778 ms` | `1.49x` |
| `1,000` | `9.085 ms` | `22.389 ms` | `2.46x` |
| `5,000` | `65.476 ms` | `539.652 ms` | `8.24x` |

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
  example rather than only stack-and-local toy programs,
- the same backend can now be reached through a stable service contract that is
  ready for open-source runtime hooks and closed-source tool wrappers.

It does not yet reproduce the full article system. Important missing pieces are:

- broad support for arbitrary C or C++ compiled WASM,
- compilation from C or WASM into model weights,
- a transformer that performs the execution directly for the full supported WASM
  surface without the current hand-written transition block,
- the article's published throughput numbers.
