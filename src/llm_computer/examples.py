"""Small WASM examples compiled from WAT."""

from __future__ import annotations

from functools import lru_cache

from llm_computer.wasm import WasmModule, compile_c_module, compile_wat_module


ARTICLE_HUNGARIAN_MATRIX: tuple[tuple[int, ...], ...] = (
    (61, 58, 35, 86, 32, 39, 41, 27, 21, 42),
    (59, 77, 97, 99, 78, 21, 89, 72, 35, 63),
    (88, 85, 37, 57, 59, 97, 37, 29, 69, 94),
    (32, 82, 53, 20, 77, 96, 21, 70, 50, 61),
    (15, 44, 81, 10, 64, 36, 56, 78, 20, 69),
    (76, 35, 87, 69, 16, 55, 26, 37, 30, 66),
    (86, 32, 74, 94, 32, 14, 24, 12, 31, 70),
    (97, 63, 20, 64, 90, 21, 28, 49, 89, 10),
    (58, 52, 27, 76, 61, 35, 17, 91, 37, 66),
    (42, 79, 61, 26, 55, 98, 70, 17, 26, 86),
)
ARTICLE_HUNGARIAN_EXPECTED_COST = 206

ARTICLE_SUDOKU_PUZZLE = "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4.."
ARTICLE_SUDOKU_EXPECTED_SOLUTION = (
    "812753649"
    "943682175"
    "675491283"
    "154237896"
    "369845721"
    "287169534"
    "521974368"
    "438526917"
    "796318452"
)
ARTICLE_SUDOKU_EXPECTED_CHECKSUM = 1_276_684_605


def _emit_int_array(values: list[int] | tuple[int, ...]) -> str:
    return ", ".join(str(value) for value in values)


def _article_sudoku_board() -> list[int]:
    return [0 if cell == "." else int(cell) for cell in ARTICLE_SUDOKU_PUZZLE]


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


@lru_cache(maxsize=None)
def article_hungarian_module() -> WasmModule:
    flat_matrix = [value for row in ARTICLE_HUNGARIAN_MATRIX for value in row]
    return compile_c_module(
        f"""
        #define N 10

        static volatile int cost[N * N] = {{{_emit_int_array(flat_matrix)}}};
        static volatile int u[N + 1];
        static volatile int v[N + 1];
        static volatile int p[N + 1];
        static volatile int way[N + 1];
        static volatile int minv[N + 1];
        static volatile int used[N + 1];

        int hungarian_10x10(void) {{
          int i = 1;
          while (i < N + 1) {{
            int j = 1;
            p[0] = i;
            int j0 = 0;
            while (j < N + 1) {{
              minv[j] = 1000000000;
              used[j] = 0;
              j += 1;
            }}

            while (1) {{
              used[j0] = 1;
              int i0 = p[j0];
              int delta = 1000000000;
              int j1 = 0;
              j = 1;
              while (j < N + 1) {{
                if (!used[j]) {{
                  int cur = cost[(i0 - 1) * N + (j - 1)] - u[i0] - v[j];
                  if (cur < minv[j]) {{
                    minv[j] = cur;
                    way[j] = j0;
                  }}
                  if (minv[j] < delta) {{
                    delta = minv[j];
                    j1 = j;
                  }}
                }}
                j += 1;
              }}

              j = 0;
              while (j < N + 1) {{
                if (used[j]) {{
                  u[p[j]] = u[p[j]] + delta;
                  v[j] = v[j] - delta;
                }} else {{
                  minv[j] = minv[j] - delta;
                }}
                j += 1;
              }}

              j0 = j1;
              if (p[j0] == 0) {{
                break;
              }}
            }}

            while (j0 != 0) {{
              int prev = way[j0];
              p[j0] = p[prev];
              j0 = prev;
            }}

            i += 1;
          }}

          return 0 - v[0];
        }}
        """,
        export_name="hungarian_10x10",
        opt_level="-O2",
    )


@lru_cache(maxsize=None)
def article_sudoku_module() -> WasmModule:
    board = _article_sudoku_board()
    row_index = [position // 9 for position in range(81)]
    col_index = [position % 9 for position in range(81)]
    box_index = [((position // 9) // 3) * 3 + ((position % 9) // 3) for position in range(81)]
    return compile_c_module(
        f"""
        static volatile int board[81] = {{{_emit_int_array(board)}}};
        static volatile int row_mask[9];
        static volatile int col_mask[9];
        static volatile int box_mask[9];
        static volatile int empties[81];
        static volatile int next_digit[81];
        static const int row_index[81] = {{{_emit_int_array(row_index)}}};
        static const int col_index[81] = {{{_emit_int_array(col_index)}}};
        static const int box_index[81] = {{{_emit_int_array(box_index)}}};

        int sudoku_checksum(void) {{
          int pos = 0;
          int empty_count = 0;
          while (pos < 81) {{
            int value = board[pos];
            if (value == 0) {{
              empties[empty_count] = pos;
              next_digit[empty_count] = 1;
              empty_count += 1;
            }} else {{
              int bit = 1 << value;
              row_mask[row_index[pos]] = row_mask[row_index[pos]] + bit;
              col_mask[col_index[pos]] = col_mask[col_index[pos]] + bit;
              box_mask[box_index[pos]] = box_mask[box_index[pos]] + bit;
            }}
            pos += 1;
          }}

          int depth = 0;
          while (1) {{
            if (depth < 0) {{
              return -1;
            }}
            if (!(depth < empty_count)) {{
              break;
            }}

            if (next_digit[depth] == 1) {{
              int best = depth;
              int best_count = 10;
              int scan = depth;
              while (scan < empty_count) {{
                int candidate_pos = empties[scan];
                int row = row_index[candidate_pos];
                int col = col_index[candidate_pos];
                int box = box_index[candidate_pos];
                int count = 0;
                int digit = 1;
                while (digit < 10) {{
                  int bit = 1 << digit;
                  if (!(row_mask[row] & bit)) {{
                    if (!(col_mask[col] & bit)) {{
                      if (!(box_mask[box] & bit)) {{
                        count += 1;
                      }}
                    }}
                  }}
                  digit += 1;
                }}
                if (count < best_count) {{
                  best = scan;
                  best_count = count;
                  if (best_count < 2) {{
                    break;
                  }}
                }}
                scan += 1;
              }}

              if (best != depth) {{
                int swap = empties[depth];
                empties[depth] = empties[best];
                empties[best] = swap;
              }}
            }}

            pos = empties[depth];
            int row = row_index[pos];
            int col = col_index[pos];
            int box = box_index[pos];
            if (board[pos] != 0) {{
              int previous = board[pos];
              int previous_bit = 1 << previous;
              row_mask[row] = row_mask[row] - previous_bit;
              col_mask[col] = col_mask[col] - previous_bit;
              box_mask[box] = box_mask[box] - previous_bit;
              board[pos] = 0;
            }}

            int digit = next_digit[depth];
            int placed = 0;
            while (digit < 10) {{
              int bit = 1 << digit;
              if (!(row_mask[row] & bit)) {{
                if (!(col_mask[col] & bit)) {{
                  if (!(box_mask[box] & bit)) {{
                    board[pos] = digit;
                    row_mask[row] = row_mask[row] + bit;
                    col_mask[col] = col_mask[col] + bit;
                    box_mask[box] = box_mask[box] + bit;
                    next_digit[depth] = digit + 1;
                    depth += 1;
                    placed = 1;
                    break;
                  }}
                }}
              }}
              digit += 1;
            }}

            if (!placed) {{
              next_digit[depth] = 1;
              depth -= 1;
            }}
          }}

          int checksum = 0;
          pos = 0;
          while (pos < 81) {{
            checksum = checksum * 11 + board[pos];
            pos += 1;
          }}
          return checksum;
        }}
        """,
        export_name="sudoku_checksum",
        opt_level="-O2",
    )
