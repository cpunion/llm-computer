"""Command-line entry point."""

from __future__ import annotations

from llm_computer.examples import (
    add_module,
    compiled_c_sum_module,
    factorial_module,
    memory_roundtrip_module,
    memory_sum_module,
    triangular_sum_module,
)
from llm_computer.executor import (
    FunctionBenchmark,
    HullTimeline,
    NaiveTimeline,
    compare_against_reference,
    online_lookup_benchmark,
    static_lookup_benchmark,
)
from llm_computer.transformer import (
    TransformerVerificationBenchmark,
    compare_transformer_to_reference,
    supports_transformer_verification,
)
from llm_computer.wasm import ReferenceWasmExecutor


def print_trace_summary(name: str, module, export_name: str = "main") -> None:
    result = ReferenceWasmExecutor(module.exported_function(export_name)).run()
    print(f"{name}: results={result.results}, steps={len(result.trace)}")
    for entry in result.trace[:10]:
        print(
            "  "
            f"step={entry.step:>3} ip={entry.ip:>2} "
            f"instr={entry.instruction:<16} value={entry.value:>6} "
            f"delta={entry.stack_delta:>2} stack={entry.stack_size:>2} "
            f"branch={int(entry.branch_taken)}"
        )
    if len(result.trace) > 10:
        print(f"  ... {len(result.trace) - 10} more trace entries")


def print_reference_check(name: str, module, export_name: str = "main") -> None:
    reference, naive = compare_against_reference(module, export_name, NaiveTimeline)
    _, hull = compare_against_reference(module, export_name, HullTimeline)
    naive_ok = reference.results == naive.results and len(reference.trace) == len(naive.trace)
    hull_ok = reference.results == hull.results and len(reference.trace) == len(hull.trace)
    print(
        f"{name}: reference_results={reference.results}, "
        f"naive_match={naive_ok}, hull_match={hull_ok}, "
        f"steps={len(reference.trace)}"
    )


def print_function_benchmark(name: str, module, export_name: str = "main") -> None:
    function = module.exported_function(export_name)
    hull = FunctionBenchmark(function, HullTimeline).run(name)
    naive = FunctionBenchmark(function, NaiveTimeline).run(name)
    speedup = naive.elapsed_s / hull.elapsed_s if hull.elapsed_s > 0 else float("inf")
    print(
        f"{name}: online_hull={hull.elapsed_s * 1e3:8.3f} ms, "
        f"naive={naive.elapsed_s * 1e3:8.3f} ms, speedup={speedup:6.2f}x, "
        f"results={hull.results}"
    )


def print_transformer_check(name: str, module, export_name: str = "main") -> None:
    function = module.exported_function(export_name)
    if not supports_transformer_verification(function):
        print(f"{name}: transformer_subset=False")
        return

    reference, naive, hull = compare_transformer_to_reference(function)
    naive_ok = reference.results == naive.results and len(reference.trace) == len(naive.trace)
    hull_ok = reference.results == hull.results and len(reference.trace) == len(hull.trace)
    print(
        f"{name}: transformer_subset=True, "
        f"naive_match={naive_ok}, hull_match={hull_ok}, "
        f"steps={len(reference.trace)}"
    )


def print_transformer_benchmark(name: str, module, export_name: str = "main") -> None:
    function = module.exported_function(export_name)
    if not supports_transformer_verification(function):
        return
    hull = TransformerVerificationBenchmark(function, HullTimeline).run(name)
    naive = TransformerVerificationBenchmark(function, NaiveTimeline).run(name)
    speedup = naive.elapsed_s / hull.elapsed_s if hull.elapsed_s > 0 else float("inf")
    print(
        f"{name}: transformer_hull={hull.elapsed_s * 1e3:8.3f} ms, "
        f"transformer_naive={naive.elapsed_s * 1e3:8.3f} ms, speedup={speedup:6.2f}x, "
        f"results={hull.results}"
    )


def main() -> None:
    print("LLM Computer WASM reimplementation")
    print()

    add_mod = add_module(3, 5)
    factorial_mod = factorial_module(7)
    triangular_mod = triangular_sum_module(200)
    memory_mod = memory_roundtrip_module(123456789)
    memory_sum_mod = memory_sum_module(200)
    compiled_c_mod = compiled_c_sum_module(10)

    print_trace_summary("add_module(3, 5)", add_mod)
    print()
    print_trace_summary("memory_roundtrip_module(123456789)", memory_mod)
    print()
    print_trace_summary("compiled_c_sum_module(10)", compiled_c_mod, export_name="sum_to")
    print()
    print_reference_check("factorial_module(7)", factorial_mod)
    print_reference_check("triangular_sum_module(200)", triangular_mod)
    print_reference_check("memory_sum_module(200)", memory_sum_mod)
    print_reference_check("compiled_c_sum_module(10)", compiled_c_mod, export_name="sum_to")
    print()
    print_transformer_check("factorial_module(7)", factorial_mod)
    print_transformer_check("triangular_sum_module(200)", triangular_mod)
    print_transformer_check("memory_sum_module(200)", memory_sum_mod)
    print_transformer_check("memory_roundtrip_module(123456789)", memory_mod)
    print_transformer_check("compiled_c_sum_module(10)", compiled_c_mod, export_name="sum_to")
    print()
    print_function_benchmark("factorial_module(7)", factorial_mod)
    print_function_benchmark("triangular_sum_module(200)", triangular_mod)
    print_function_benchmark("memory_sum_module(200)", memory_sum_mod)
    print_function_benchmark("compiled_c_sum_module(10)", compiled_c_mod, export_name="sum_to")
    print()
    print_transformer_benchmark("factorial_module(7)", factorial_mod)
    print_transformer_benchmark("triangular_sum_module(200)", triangular_mod)
    print_transformer_benchmark("memory_sum_module(200)", memory_sum_mod)
    print_transformer_benchmark("compiled_c_sum_module(10)", compiled_c_mod, export_name="sum_to")
    print()

    print("Static lookup benchmark")
    for length, hull_us, naive_us, speedup in static_lookup_benchmark([100, 500, 1_000, 5_000]):
        print(
            f"  n={length:>5}: hull={hull_us:8.3f} us, "
            f"naive={naive_us:8.3f} us, speedup={speedup:6.2f}x"
        )

    print()
    print("Online append-only lookup benchmark")
    for length, hull_ms, naive_ms, speedup in online_lookup_benchmark([100, 500, 1_000, 5_000]):
        print(
            f"  n={length:>5}: online_hull={hull_ms:8.3f} ms, "
            f"naive={naive_ms:8.3f} ms, speedup={speedup:6.2f}x"
        )


if __name__ == "__main__":
    main()
