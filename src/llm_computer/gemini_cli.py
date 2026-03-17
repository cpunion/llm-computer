"""Command-line entry point for the Gemini closed-source execution scaffold."""

from __future__ import annotations

import argparse
import json

from llm_computer.gemini_integration import DEFAULT_GEMINI_MODEL, GeminiExecutionRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Gemini execution scaffold.")
    parser.add_argument("--model", default=DEFAULT_GEMINI_MODEL, help="Gemini model name.")
    parser.add_argument("--prompt", required=True, help="User prompt to send to Gemini.")
    parser.add_argument("--system", default="You are a precise engineering assistant.", help="Optional system prompt.")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature.")
    parser.add_argument("--force-tool-use", action="store_true", help="Force Gemini to call the execution tool.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    runtime = GeminiExecutionRuntime.from_env(model=args.model)
    result = runtime.run(
        args.prompt,
        system_prompt=args.system,
        temperature=args.temperature,
        force_tool_use=args.force_tool_use,
    )
    print(result.text)
    print()
    print(
        json.dumps(
            {
                "model": result.model,
                "tool_calls": result.tool_calls,
                "used_execution": result.used_execution,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
