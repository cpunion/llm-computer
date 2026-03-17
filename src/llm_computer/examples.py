"""Small WASM examples compiled from WAT."""

from __future__ import annotations

from functools import lru_cache

from llm_computer.wasm import WasmModule, compile_c_module, compile_wat_module


@lru_cache(maxsize=None)
def add_module(lhs: int, rhs: int) -> WasmModule:
    return compile_wat_module(
        f"""
        (module
          (func (export "main") (result i32)
            i32.const {lhs}
            i32.const {rhs}
            i32.add
          )
        )
        """
    )


@lru_cache(maxsize=None)
def factorial_module(n: int) -> WasmModule:
    return compile_wat_module(
        f"""
        (module
          (func (export "main") (result i32)
            (local i32 i32)
            i32.const 1
            local.set 0
            i32.const {n}
            local.set 1
            block
              loop
                local.get 1
                i32.eqz
                br_if 1
                local.get 0
                local.get 1
                i32.mul
                local.set 0
                local.get 1
                i32.const 1
                i32.sub
                local.set 1
                br 0
              end
            end
            local.get 0
          )
        )
        """
    )


@lru_cache(maxsize=None)
def triangular_sum_module(n: int) -> WasmModule:
    return compile_wat_module(
        f"""
        (module
          (func (export "main") (result i32)
            (local i32 i32)
            i32.const 0
            local.set 0
            i32.const {n}
            local.set 1
            block
              loop
                local.get 1
                i32.eqz
                br_if 1
                local.get 0
                local.get 1
                i32.add
                local.set 0
                local.get 1
                i32.const 1
                i32.sub
                local.set 1
                br 0
              end
            end
            local.get 0
          )
        )
        """
    )


@lru_cache(maxsize=None)
def memory_roundtrip_module(value: int) -> WasmModule:
    return compile_wat_module(
        f"""
        (module
          (memory 1)
          (func (export "main") (result i32)
            i32.const 0
            i32.const {value}
            i32.store
            i32.const 0
            i32.load
          )
        )
        """
    )


@lru_cache(maxsize=None)
def memory_sum_module(n: int) -> WasmModule:
    return compile_wat_module(
        f"""
        (module
          (memory 1)
          (func (export "main") (result i32)
            (local i32)
            i32.const 0
            i32.const 0
            i32.store
            i32.const {n}
            local.set 0
            block
              loop
                local.get 0
                i32.eqz
                br_if 1
                i32.const 0
                i32.const 0
                i32.load
                local.get 0
                i32.add
                i32.store
                local.get 0
                i32.const 1
                i32.sub
                local.set 0
                br 0
              end
            end
            i32.const 0
            i32.load
          )
        )
        """
    )


@lru_cache(maxsize=None)
def compiled_c_sum_module(limit: int) -> WasmModule:
    return compile_c_module(
        f"""
        volatile int limit = {limit};

        int sum_to(void) {{
          int s = 0;
          for (int i = 0; i < limit; ++i) {{
            s += i;
          }}
          return s;
        }}
        """,
        export_name="sum_to",
        opt_level="-O2",
    )
