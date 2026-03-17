"""Generate a long-form article and visual assets for the five implementation ladder."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date
import json
from math import log10
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
ASSETS_DIR = DOCS_DIR / "assets"
REMOTION_DATA_PATH = ROOT / "visuals" / "remotion" / "src" / "generated-data.js"
ORIGINAL_ARTICLE = {
    "title": "Can LLMs Be Computers?",
    "subtitle": "Executing programs inside transformers with exponentially faster inference",
    "authors": "Christos Tzamos together with others at Percepta",
    "published": "Mar 11, 2026",
    "url": "https://www.percepta.ai/blog/can-llms-be-computers",
}


@dataclass(slots=True)
class MethodStory:
    depth_rank: int
    method_id: str
    title: str
    short_label: str
    category: str
    depth_caption: str
    execution_boundary: str
    implementation_summary: str
    implementation_notes: list[str]
    testing_notes: list[str]
    comparison: dict[str, object]
    validation_flags: dict[str, bool]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        return payload


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "-"
    if value < 1:
        return f"{value * 1e3:.2f} ms"
    return f"{value:.3f} s"


def _method_metadata() -> dict[str, dict[str, object]]:
    return {
        "reference_direct": {
            "depth_rank": 1,
            "title": "Reference Direct",
            "short_label": "Reference",
            "category": "direct",
            "depth_caption": "Pure semantic control with no model in the loop.",
            "execution_boundary": "The service calls the reference WASM executor directly.",
            "implementation_summary": "This is the cleanest semantic baseline: parse WASM, execute it with ordinary mutable state, and return the result without any model orchestration.",
            "implementation_notes": [
                "Uses `ReferenceWasmExecutor` as the canonical semantics oracle.",
                "Bypasses prompt protocols, wrappers, and tool calls entirely.",
                "Defines the trace shape that every deeper implementation must preserve.",
            ],
            "testing_notes": [
                "Passed the five-way comparison scenario with final value `42`.",
                "Validated Hungarian end-to-end with result `206`.",
                "Validated the full article Sudoku checksum `1276684605` in `22,370,167` steps.",
            ],
            "validation_flags": {
                "toy_scenario": True,
                "real_model": False,
                "article_hungarian": True,
                "sudoku_full": True,
                "sudoku_prefix": True,
                "native_block": False,
                "tool_call": False,
                "structured_capture": False,
            },
        },
        "append_only_naive_direct": {
            "depth_rank": 2,
            "title": "Append-Only Naive Direct",
            "short_label": "Append-only Naive",
            "category": "direct",
            "depth_caption": "The article mechanism without model integration or geometric acceleration.",
            "execution_boundary": "The service calls the append-only executor with a naive timeline scan.",
            "implementation_summary": "This is the first mechanism-faithful executor: state is reconstructed from append-only writes, but retrieval still scans the whole history instead of using a hull-backed fast path.",
            "implementation_notes": [
                "Replaces mutable locals and stack with append-only state timelines.",
                "Uses the same request/response boundary as other direct backends.",
                "Serves as the control for whether the hull trick actually matters.",
            ],
            "testing_notes": [
                "Passed the five-way comparison scenario with final value `42`.",
                "Validated Hungarian end-to-end with result `206`.",
                "Matched the reference Sudoku prefix state through `10,000` steps.",
            ],
            "validation_flags": {
                "toy_scenario": True,
                "real_model": False,
                "article_hungarian": True,
                "sudoku_full": False,
                "sudoku_prefix": True,
                "native_block": False,
                "tool_call": False,
                "structured_capture": False,
            },
        },
        "closed_source_sidecar": {
            "depth_rank": 3,
            "title": "Closed-Source Sidecar",
            "short_label": "Closed-source Sidecar",
            "category": "closed_source",
            "depth_caption": "A hosted model delegates execution through a strict tool boundary.",
            "execution_boundary": "Gemini plans; the sidecar executes; Gemini narrates the final answer.",
            "implementation_summary": "This is the best available path for closed-weight APIs: the model remains a planner, while the execution contract is enforced through a strict tool schema and the shared sidecar service.",
            "implementation_notes": [
                "Uses `gemini-3-flash-preview` with forced tool use.",
                "Keeps the execution backend identical to the open-source path.",
                "Cannot move execution inside model weights because runtime internals are unavailable.",
            ],
            "testing_notes": [
                "Passed the five-way comparison scenario with final value `42`.",
                "Recorded `tool_calls=1` in live validation.",
                "Backed by dedicated Gemini integration tests plus the stage-3 and stage-10 validations.",
            ],
            "validation_flags": {
                "toy_scenario": True,
                "real_model": True,
                "article_hungarian": False,
                "sudoku_full": False,
                "sudoku_prefix": False,
                "native_block": False,
                "tool_call": True,
                "structured_capture": False,
            },
        },
        "open_source_wrapper": {
            "depth_rank": 4,
            "title": "Open-Source Wrapper",
            "short_label": "Open-source Wrapper",
            "category": "open_source",
            "depth_caption": "An open-weight runtime intercepts execution requests at the prompt boundary.",
            "execution_boundary": "Qwen emits a structured execution request; the runtime resolves it and feeds back a response span.",
            "implementation_summary": "This path keeps execution outside the model block graph, but it moves orchestration inside the open runtime: request extraction, structured capture, and response injection are all handled locally.",
            "implementation_notes": [
                "Validated with `Qwen/Qwen2.5-0.5B-Instruct` through `Transformers`.",
                "Supports tagged requests, structured capture, and prefilled structured prompt mode.",
                "Still round-trips through runtime feedback rather than a native execution block.",
            ],
            "testing_notes": [
                "Passed the five-way comparison scenario with final value `42`.",
                "Recorded `intercepted_requests=1` and `structured_captures=1`.",
                "Covered by stages 4 through 8 plus the comparison harness.",
            ],
            "validation_flags": {
                "toy_scenario": True,
                "real_model": True,
                "article_hungarian": False,
                "sudoku_full": False,
                "sudoku_prefix": False,
                "native_block": False,
                "tool_call": False,
                "structured_capture": True,
            },
        },
        "open_source_execution_block": {
            "depth_rank": 5,
            "title": "Open-Source Execution Block",
            "short_label": "Execution Block",
            "category": "open_source",
            "depth_caption": "The closest current path to in-model execution without replacing real model weights.",
            "execution_boundary": "Qwen still emits the request, but the runtime resolves it natively and returns compact execution feedback instead of an `exec_response` text block.",
            "implementation_summary": "This is the deepest current integration: open-weight generation stays in the loop, yet the execution round-trip is resolved through a native execution-block path instead of a wrapper-only text protocol.",
            "implementation_notes": [
                "Pins the backend to `transformer_hull` for the native execution round.",
                "Removes the `exec_response` text loop from the hot path.",
                "Acts as the bridge between today's wrapper integration and tomorrow's true in-model execution heads.",
            ],
            "testing_notes": [
                "Passed the five-way comparison scenario with final value `42`.",
                "Recorded `native_execution_rounds=1` with no runtime answer fallback.",
                "Covered by stage 9, the comparison harness, and the transformer regression suite.",
            ],
            "validation_flags": {
                "toy_scenario": True,
                "real_model": True,
                "article_hungarian": False,
                "sudoku_full": False,
                "sudoku_prefix": False,
                "native_block": True,
                "tool_call": False,
                "structured_capture": True,
            },
        },
    }


def build_method_stories(
    comparison_report: dict[str, object],
    article_example_report: dict[str, object],
    sudoku_report: dict[str, object],
) -> list[MethodStory]:
    comparison_by_id = {row["method_id"]: row for row in comparison_report["results"]}
    metadata = _method_metadata()
    methods: list[MethodStory] = []
    for method_id, config in metadata.items():
        comparison = comparison_by_id[method_id]
        methods.append(
            MethodStory(
                depth_rank=int(config["depth_rank"]),
                method_id=method_id,
                title=str(config["title"]),
                short_label=str(config["short_label"]),
                category=str(config["category"]),
                depth_caption=str(config["depth_caption"]),
                execution_boundary=str(config["execution_boundary"]),
                implementation_summary=str(config["implementation_summary"]),
                implementation_notes=list(config["implementation_notes"]),
                testing_notes=list(config["testing_notes"]),
                comparison=comparison,
                validation_flags=dict(config["validation_flags"]),
            )
        )
    methods.sort(key=lambda item: item.depth_rank)
    return methods


def _svg_header(width: int, height: int, background: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none">',
        "<defs>",
        '<linearGradient id="heroGradient" x1="0" y1="0" x2="1" y2="1">',
        '<stop offset="0%" stop-color="#F97316"/>',
        '<stop offset="100%" stop-color="#0F766E"/>',
        "</linearGradient>",
        '<filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">',
        '<feDropShadow dx="0" dy="8" stdDeviation="16" flood-color="#0f172a" flood-opacity="0.12"/>',
        "</filter>",
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
    ]


def _svg_footer() -> list[str]:
    return ["</svg>"]


def render_implementation_ladder_svg(methods: list[MethodStory]) -> str:
    width = 1400
    height = 1040
    lines = _svg_header(width, height, "#F7F2E8")
    lines.extend(
        [
            '<text x="80" y="110" font-size="54" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">Five Ways We Moved Execution Closer to the Model</text>',
            '<text x="80" y="156" font-size="24" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">Ordered by execution depth, not by raw speed.</text>',
        ]
    )

    colors = ["#E2E8F0", "#FED7AA", "#FDE68A", "#BFDBFE", "#99F6E4"]
    border = ["#94A3B8", "#F97316", "#D97706", "#2563EB", "#0F766E"]
    card_height = 146
    top = 210
    for index, method in enumerate(methods):
        y = top + index * 152
        lines.append(
            f'<rect x="80" y="{y}" width="1240" height="{card_height}" rx="28" fill="{colors[index]}" stroke="{border[index]}" stroke-width="4" filter="url(#softShadow)"/>'
        )
        lines.append(
            f'<circle cx="138" cy="{y + 44}" r="28" fill="{border[index]}"/>'
        )
        lines.append(
            f'<text x="138" y="{y + 53}" text-anchor="middle" font-size="28" font-family="JetBrains Mono, Menlo, monospace" font-weight="700" fill="#FFF">{method.depth_rank}</text>'
        )
        lines.append(
            f'<text x="190" y="{y + 52}" font-size="34" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">{method.title}</text>'
        )
        lines.append(
            f'<text x="190" y="{y + 86}" font-size="22" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#334155">{method.depth_caption}</text>'
        )
        lines.append(
            f'<text x="190" y="{y + 120}" font-size="20" font-family="JetBrains Mono, Menlo, monospace" fill="#0F172A">{method.execution_boundary}</text>'
        )
        if index < len(methods) - 1:
            arrow_y1 = y + card_height
            arrow_y2 = y + 152
            lines.append(
                f'<path d="M700 {arrow_y1 + 8} L700 {arrow_y2 - 14}" stroke="#94A3B8" stroke-width="6" stroke-linecap="round" stroke-dasharray="10 10"/>'
            )
            lines.append(
                f'<path d="M700 {arrow_y2 - 6} L686 {arrow_y2 - 28} L714 {arrow_y2 - 28} Z" fill="#94A3B8"/>'
            )

    lines.extend(_svg_footer())
    return "\n".join(lines)


def render_latency_svg(methods: list[MethodStory]) -> str:
    width = 1400
    height = 820
    lines = _svg_header(width, height, "#FFF8EE")
    lines.extend(
        [
            '<text x="80" y="110" font-size="52" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">Latency on the Canonical 6 × 7 Scenario</text>',
            '<text x="80" y="156" font-size="24" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">End-to-end time from the recorded five-way comparison. The x-axis is log-scaled.</text>',
        ]
    )
    max_log = max(log10(float(method.comparison["end_to_end_s"])) for method in methods)
    min_log = min(log10(float(method.comparison["end_to_end_s"])) for method in methods)
    usable = 1000
    bar_x = 280
    top = 220
    palette = {
        "direct": "#F97316",
        "open_source": "#2563EB",
        "closed_source": "#0F766E",
    }
    for index, method in enumerate(methods):
        y = top + index * 102
        elapsed = float(method.comparison["end_to_end_s"])
        normalized = 0.2 if max_log == min_log else (log10(elapsed) - min_log) / (max_log - min_log)
        width_px = 180 + normalized * usable
        color = palette[method.category]
        lines.append(
            f'<text x="80" y="{y + 42}" font-size="28" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">{method.short_label}</text>'
        )
        lines.append(
            f'<rect x="{bar_x}" y="{y}" width="{width_px:.1f}" height="54" rx="18" fill="{color}" opacity="0.9"/>'
        )
        lines.append(
            f'<text x="{bar_x + 18}" y="{y + 36}" font-size="22" font-family="JetBrains Mono, Menlo, monospace" fill="#fff">{_format_seconds(elapsed)}</text>'
        )
        notes = str(method.comparison["notes"])
        lines.append(
            f'<text x="{bar_x}" y="{y + 82}" font-size="18" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">{notes}</text>'
        )

    lines.extend(_svg_footer())
    return "\n".join(lines)


def render_validation_matrix_svg(methods: list[MethodStory]) -> str:
    width = 1500
    height = 760
    lines = _svg_header(width, height, "#F6FBFB")
    lines.extend(
        [
            '<text x="80" y="110" font-size="52" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">Validation Matrix</text>',
            '<text x="80" y="156" font-size="24" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">What each implementation has actually demonstrated, not just what it is intended to become.</text>',
        ]
    )
    columns = [
        ("toy_scenario", "Toy 42"),
        ("real_model", "Real Model"),
        ("article_hungarian", "Hungarian"),
        ("sudoku_full", "Sudoku Full"),
        ("sudoku_prefix", "Sudoku Prefix"),
        ("structured_capture", "Structured"),
        ("native_block", "Native Block"),
        ("tool_call", "Tool Call"),
    ]
    start_x = 430
    start_y = 240
    row_h = 86
    col_w = 120
    lines.append('<rect x="80" y="200" width="1340" height="500" rx="28" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="3"/>')
    lines.append(f'<text x="120" y="{start_y - 24}" font-size="22" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">Implementation</text>')
    for col_index, (_, label) in enumerate(columns):
        x = start_x + col_index * col_w
        lines.append(f'<text x="{x + col_w/2:.0f}" y="{start_y - 24}" text-anchor="middle" font-size="18" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">{label}</text>')
    for row_index, method in enumerate(methods):
        y = start_y + row_index * row_h
        fill = "#FFF7ED" if row_index % 2 == 0 else "#FFFFFF"
        lines.append(f'<rect x="92" y="{y - 34}" width="1316" height="72" rx="18" fill="{fill}"/>')
        lines.append(f'<text x="120" y="{y + 8}" font-size="24" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">{method.title}</text>')
        for col_index, (key, _) in enumerate(columns):
            x = start_x + col_index * col_w + col_w / 2
            enabled = method.validation_flags[key]
            symbol = "✓" if enabled else "–"
            color = "#0F766E" if enabled else "#94A3B8"
            lines.append(f'<text x="{x:.0f}" y="{y + 10}" text-anchor="middle" font-size="34" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="{color}">{symbol}</text>')
    lines.extend(_svg_footer())
    return "\n".join(lines)


def render_article_examples_svg(article_report: dict[str, object]) -> str:
    width = 1500
    height = 860
    lines = _svg_header(width, height, "#FFFDF7")
    lines.extend(
        [
            '<text x="80" y="110" font-size="52" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">Article Examples: Hungarian and Sudoku</text>',
            '<text x="80" y="156" font-size="24" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">The same repository now validates the article’s published examples instead of only toy arithmetic.</text>',
        ]
    )
    hungarian_rows = [row for row in article_report["results"] if row["example_id"] == "hungarian_10x10"]
    sudoku_row = next(row for row in article_report["results"] if row["example_id"] == "sudoku_checksum")
    panel_y = 230
    lines.append('<rect x="80" y="210" width="650" height="560" rx="30" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="3"/>')
    lines.append('<rect x="770" y="210" width="650" height="560" rx="30" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="3"/>')
    lines.append('<text x="120" y="280" font-size="34" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">Hungarian 10×10</text>')
    lines.append('<text x="810" y="280" font-size="34" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">Sudoku</text>')
    palette = {"reference": "#0F766E", "append_only_naive": "#F97316", "append_only_hull": "#2563EB", "transformer_hull": "#7C3AED"}
    max_elapsed = max(float(row["elapsed_s"]) for row in hungarian_rows)
    for index, row in enumerate(hungarian_rows):
        y = 340 + index * 96
        bar_w = 420 * float(row["elapsed_s"]) / max_elapsed
        mode = str(row["mode"])
        lines.append(f'<text x="120" y="{y + 26}" font-size="24" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#0F172A">{mode}</text>')
        lines.append(f'<rect x="300" y="{y}" width="{bar_w:.1f}" height="40" rx="14" fill="{palette[mode]}"/>')
        lines.append(f'<text x="312" y="{y + 27}" font-size="18" font-family="JetBrains Mono, Menlo, monospace" fill="#fff">{_format_seconds(float(row["elapsed_s"]))}</text>')
        lines.append(f'<text x="300" y="{y + 66}" font-size="18" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">result={row["result"]} steps={row["steps"]}</text>')
    lines.append(f'<text x="810" y="344" font-size="24" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">Reference checksum</text>')
    lines.append(f'<text x="810" y="420" font-size="64" font-family="JetBrains Mono, Menlo, monospace" font-weight="700" fill="url(#heroGradient)">{sudoku_row["result"]}</text>')
    lines.append(f'<text x="810" y="474" font-size="22" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#0F172A">steps: {sudoku_row["steps"]:,}</text>')
    lines.append(f'<text x="810" y="512" font-size="22" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#0F172A">elapsed: {_format_seconds(float(sudoku_row["elapsed_s"]))}</text>')
    lines.append(f'<text x="810" y="568" font-size="22" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">Puzzle: {article_report["sudoku_puzzle"][:27]}...</text>')
    lines.append('<text x="810" y="624" font-size="22" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">Transformer subset: yes</text>')
    lines.append('<text x="810" y="680" font-size="22" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">Meaning: the long example exists inside the same opcode subset as the tiny verifier.</text>')
    lines.extend(_svg_footer())
    return "\n".join(lines)


def render_sudoku_prefix_svg(sudoku_report: dict[str, object]) -> str:
    width = 1500
    height = 900
    lines = _svg_header(width, height, "#F8FAFC")
    lines.extend(
        [
            '<text x="80" y="110" font-size="52" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">Sudoku Prefix Validation Frontier</text>',
            '<text x="80" y="156" font-size="24" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">The repository validates exact snapshot equivalence before attempting expensive full-length runs.</text>',
        ]
    )
    rows = [row for row in sudoku_report["prefix_results"] if row["mode"] != "reference"]
    budgets = sorted({int(row["budget"]) for row in rows})
    modes = ["append_only_naive", "append_only_hull", "transformer_hull"]
    palette = {"append_only_naive": "#F97316", "append_only_hull": "#2563EB", "transformer_hull": "#7C3AED"}
    top = 280
    left = 160
    cluster_w = 380
    max_elapsed = max(float(row["elapsed_s"]) for row in rows)
    for budget_index, budget in enumerate(budgets):
        cluster_x = left + budget_index * cluster_w
        lines.append(f'<text x="{cluster_x + 90}" y="240" font-size="30" font-family="JetBrains Mono, Menlo, monospace" font-weight="700" fill="#0F172A">{budget:,} steps</text>')
        budget_rows = {row["mode"]: row for row in rows if int(row["budget"]) == budget}
        for mode_index, mode in enumerate(modes):
            row = budget_rows.get(mode)
            if row is None:
                continue
            x = cluster_x + mode_index * 100
            bar_h = 360 * float(row["elapsed_s"]) / max_elapsed
            y = top + 380 - bar_h
            lines.append(f'<rect x="{x}" y="{y:.1f}" width="72" height="{bar_h:.1f}" rx="18" fill="{palette[mode]}"/>')
            lines.append(f'<text x="{x + 36}" y="{top + 430}" text-anchor="middle" font-size="18" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#0F172A">{mode.replace("_", " ")}</text>')
            lines.append(f'<text x="{x + 36}" y="{y - 12:.1f}" text-anchor="middle" font-size="16" font-family="JetBrains Mono, Menlo, monospace" fill="#334155">{_format_seconds(float(row["elapsed_s"]))}</text>')
            if bool(row["matches_reference"]):
                lines.append(f'<text x="{x + 36}" y="{top + 466}" text-anchor="middle" font-size="22" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F766E">matches</text>')
    lines.append('<text x="80" y="820" font-size="20" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">All recorded rows matched the reference snapshot. The `append_only_naive` path is intentionally capped at 10,000 steps in the default validation stage.</text>')
    lines.extend(_svg_footer())
    return "\n".join(lines)


def render_paths_svg(methods: list[MethodStory]) -> str:
    width = 1500
    height = 940
    lines = _svg_header(width, height, "#FEFCE8")
    lines.extend(
        [
            '<text x="80" y="110" font-size="52" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">Where Execution Actually Happens</text>',
            '<text x="80" y="156" font-size="24" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">The same final answer `42` can come from very different runtime boundaries.</text>',
        ]
    )
    colors = {"direct": "#F97316", "open_source": "#2563EB", "closed_source": "#0F766E"}
    top = 220
    for index, method in enumerate(methods):
        y = top + index * 132
        color = colors[method.category]
        lines.append(f'<rect x="80" y="{y}" width="1340" height="96" rx="26" fill="#fff" stroke="#CBD5E1" stroke-width="3"/>')
        lines.append(f'<text x="120" y="{y + 38}" font-size="30" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="#0F172A">{method.title}</text>')
        lines.append(f'<text x="120" y="{y + 70}" font-size="18" font-family="Avenir Next, Trebuchet MS, sans-serif" fill="#475569">{method.execution_boundary}</text>')
        nodes = ["Prompt", "Model", "Runtime", "Executor", "Answer"]
        node_x = [740, 900, 1060, 1220, 1360]
        for node_index, label in enumerate(nodes):
            fill = "#E2E8F0"
            if label == "Executor":
                fill = color
            if method.category == "direct" and label in {"Prompt", "Model"}:
                fill = "#F1F5F9"
            if method.category == "closed_source" and label == "Model":
                fill = "#CCFBF1"
            if method.category == "open_source" and label == "Model":
                fill = "#DBEAFE"
            lines.append(f'<rect x="{node_x[node_index] - 58}" y="{y + 20}" width="108" height="44" rx="16" fill="{fill}"/>')
            text_color = "#fff" if label == "Executor" else "#0F172A"
            lines.append(f'<text x="{node_x[node_index] - 4}" y="{y + 49}" text-anchor="middle" font-size="20" font-family="Avenir Next, Trebuchet MS, sans-serif" font-weight="700" fill="{text_color}">{label}</text>')
            if node_index > 0:
                x1 = node_x[node_index - 1] + 54
                x2 = node_x[node_index] - 66
                lines.append(f'<path d="M{x1} {y + 42} L{x2} {y + 42}" stroke="#94A3B8" stroke-width="4" stroke-linecap="round"/>')
        lines.append(f'<text x="740" y="{y + 82}" font-size="16" font-family="JetBrains Mono, Menlo, monospace" fill="{color}">{str(method.comparison["notes"])}</text>')
    lines.extend(_svg_footer())
    return "\n".join(lines)


def render_article_markdown(
    methods: list[MethodStory],
    comparison_report: dict[str, object],
    article_report: dict[str, object],
    sudoku_report: dict[str, object],
) -> str:
    environment = comparison_report["environment"]
    lines = [
        "# Five Ways We Tried to Execute Programs with LLMs",
        "",
        "![Animated overview](assets/five-implementation-overview.gif)",
        "",
        "## Original Reference",
        "",
        f"This project article is a validation and implementation report inspired by Percepta's original post: [{ORIGINAL_ARTICLE['title']}]({ORIGINAL_ARTICLE['url']}).",
        "",
        f"- Original title: *{ORIGINAL_ARTICLE['title']}*",
        f"- Original subtitle: {ORIGINAL_ARTICLE['subtitle']}",
        f"- Published by: {ORIGINAL_ARTICLE['authors']}",
        f"- Published on: {ORIGINAL_ARTICLE['published']}",
        f"- Original link: {ORIGINAL_ARTICLE['url']}",
        "",
        "## TL;DR",
        "",
        "We now have five working execution paths in one repository, ordered from the shallowest semantic baseline to the deepest current open-weight integration. The point of the ladder is not that every deeper layer is already faster. The point is that each layer moves the execution boundary closer to the model while preserving a single underlying execution contract.",
        "",
        f"The live comparison was recorded on `{environment['open_source_model']}` for the open-source path, `{environment['closed_source_model']}` for the closed-source path, and `mps` as the device. All five methods returned the same final value `42` on the canonical WASM scenario.",
        "",
        "![Implementation ladder](assets/five-implementation-ladder.png)",
        "",
        "## Why This Ladder Matters",
        "",
        "Most discussions about tool use versus in-model execution collapse too many design choices into one question. In practice there are several distinct integration layers:",
        "",
        "1. A semantic baseline that defines correct execution.",
        "2. A mechanism baseline that already uses append-only state recovery.",
        "3. A hosted-model path that can only call out to a sidecar.",
        "4. An open-weight wrapper that intercepts structured requests inside the local runtime.",
        "5. A native open-source execution block that removes the text round-trip and starts to resemble an embedded executor.",
        "",
        "The important result is that the repository now exercises all five layers with the same service contract and the same published article examples.",
        "",
        "![Execution boundaries](assets/five-implementation-paths.png)",
        "",
        "## The Five Implementations",
        "",
    ]

    for method in methods:
        lines.extend(
            [
                f"### {method.depth_rank}. {method.title}",
                "",
                method.implementation_summary,
                "",
                f"**Execution boundary.** {method.execution_boundary}",
                "",
                f"**Canonical 6 × 7 run.** `{_format_seconds(float(method.comparison['end_to_end_s']))}` end-to-end, final value `{method.comparison['final_value']}`.",
                "",
                "**Implementation notes**",
                "",
            ]
        )
        for note in method.implementation_notes:
            lines.append(f"- {note}")
        lines.extend(["", "**Testing status**", ""])
        for note in method.testing_notes:
            lines.append(f"- {note}")
        lines.append("")

    lines.extend(
        [
            "## Comparison Snapshot",
            "",
            "![Latency chart](assets/five-implementation-latency.png)",
            "",
            "| Depth | Method | Category | End-to-end | Used execution | Key runtime signal |",
            "| ---: | --- | --- | ---: | --- | --- |",
        ]
    )
    for method in methods:
        key_signal = "-"
        if method.comparison["native_execution_rounds"]:
            key_signal = f"native_execution_rounds={method.comparison['native_execution_rounds']}"
        elif method.comparison["structured_captures"]:
            key_signal = f"structured_captures={method.comparison['structured_captures']}"
        elif method.comparison["tool_calls"]:
            key_signal = f"tool_calls={method.comparison['tool_calls']}"
        lines.append(
            f"| {method.depth_rank} | {method.title} | {method.category.replace('_', ' ')} | {_format_seconds(float(method.comparison['end_to_end_s']))} | {'yes' if method.comparison['used_execution'] else 'no'} | {key_signal} |"
        )

    lines.extend(
        [
            "",
            "## What the Article Examples Added",
            "",
            "The original repository already handled toy arithmetic and small compiled-C examples. The next requirement was stronger: validate the examples that the Percepta article actually shows to readers. That changed the quality bar for the project.",
            "",
            "![Article examples](assets/article-example-results.png)",
            "",
            f"The published Hungarian example now succeeds across four local backends with the same result `{article_report['hungarian_expected_cost']}`. The published Sudoku puzzle now succeeds end-to-end under the reference WASM executor with checksum `{sudoku_report['checksum_result']['result']}`.",
            "",
            "The Sudoku story is especially important because it separates two claims that are often blurred together:",
            "",
            "- full-result correctness under the semantic reference executor,",
            "- prefix-state equivalence under the append-only and transformer-style paths.",
            "",
            "That distinction keeps the article honest: the long puzzle is fully solved in the repository, but only the reference path currently completes the entire `22M+` step run as part of the preserved validation artifacts.",
            "",
            "![Sudoku prefix validation](assets/sudoku-prefix-validation.png)",
            "",
            "## What Each Layer Taught Us",
            "",
            "- The reference path is still indispensable. It is the only clean oracle for semantic correctness.",
            "- The append-only naive path proves that the article mechanism is not just an optimization trick. State really can be reconstructed from append-only writes.",
            "- The closed-source sidecar path proves that hosted APIs can participate, but only through a hard tool boundary.",
            "- The open-source wrapper path proves that runtime interception can turn a plain local model into an execution-aware system without changing model weights.",
            "- The open-source execution-block path is the most promising bridge to the article’s end state because it removes the text response loop and starts to behave like a native execution lane.",
            "",
            "## Validation Matrix",
            "",
            "![Validation matrix](assets/five-implementation-validation-matrix.png)",
            "",
            "## Final Summary",
            "",
            "The repository now has five distinct implementations that all return the same canonical answer but represent very different architectural commitments. The deeper the implementation, the closer execution moves to the model boundary. The harder the article example, the more important it becomes to preserve separate validation artifacts instead of folding everything into a single headline claim.",
            "",
            "Today’s strongest supported statement is therefore narrower and more useful than marketing language:",
            "",
            "> We can now compare five concrete execution layers inside one codebase, validate them against the same semantic oracle, and demonstrate that the article’s Hungarian and Sudoku examples survive that ladder instead of only toy arithmetic.",
            "",
            "The remaining gap is also clear: a true execution-head path inside a real open-weight model still has to replace the last deterministic Python transition layer.",
            "",
            "## Source Files",
            "",
            f"- Original article: {ORIGINAL_ARTICLE['url']}",
            "- `docs/five-way-comparison.json`",
            "- `docs/article-example-validation.json`",
            "- `docs/sudoku-result-validation.json`",
            "- `docs/stage-validation-log.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def render_remotion_data_js(
    methods: list[MethodStory],
    article_report: dict[str, object],
    sudoku_report: dict[str, object],
) -> str:
    payload = {
        "generated_on": date.today().isoformat(),
        "methods": [method.to_dict() for method in methods],
        "articleExamples": article_report,
        "sudokuReport": sudoku_report,
    }
    return "export const articleData = " + json.dumps(payload, indent=2, sort_keys=True) + ";\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_assets(assets_dir: Path, methods: list[MethodStory], article_report: dict[str, object], sudoku_report: dict[str, object]) -> None:
    write_text(assets_dir / "five-implementation-ladder.svg", render_implementation_ladder_svg(methods))
    write_text(assets_dir / "five-implementation-latency.svg", render_latency_svg(methods))
    write_text(assets_dir / "five-implementation-validation-matrix.svg", render_validation_matrix_svg(methods))
    write_text(assets_dir / "article-example-results.svg", render_article_examples_svg(article_report))
    write_text(assets_dir / "sudoku-prefix-validation.svg", render_sudoku_prefix_svg(sudoku_report))
    write_text(assets_dir / "five-implementation-paths.svg", render_paths_svg(methods))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the five-implementation article and visual assets.")
    parser.add_argument("--comparison-report", default=str(DOCS_DIR / "five-way-comparison.json"))
    parser.add_argument("--article-example-report", default=str(DOCS_DIR / "article-example-validation.json"))
    parser.add_argument("--sudoku-report", default=str(DOCS_DIR / "sudoku-result-validation.json"))
    parser.add_argument("--article-output", default=str(DOCS_DIR / "five-implementations-article.md"))
    parser.add_argument("--assets-dir", default=str(ASSETS_DIR))
    parser.add_argument("--remotion-data-output", default=str(REMOTION_DATA_PATH))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    comparison_report = _read_json(Path(args.comparison_report))
    article_report = _read_json(Path(args.article_example_report))
    sudoku_report = _read_json(Path(args.sudoku_report))

    methods = build_method_stories(comparison_report, article_report, sudoku_report)
    article = render_article_markdown(methods, comparison_report, article_report, sudoku_report)

    write_text(Path(args.article_output), article)
    generate_assets(Path(args.assets_dir), methods, article_report, sudoku_report)
    write_text(Path(args.remotion_data_output), render_remotion_data_js(methods, article_report, sudoku_report))
    print(
        json.dumps(
            {
                "article_output": args.article_output,
                "assets_dir": args.assets_dir,
                "remotion_data_output": args.remotion_data_output,
                "methods": [method.method_id for method in methods],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
