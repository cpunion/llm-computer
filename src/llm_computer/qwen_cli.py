"""Command-line entry point for the Qwen3 plus Transformers scaffold."""

from __future__ import annotations

import argparse
import json

from llm_computer.qwen_transformers import DEFAULT_QWEN_MODEL_ID, GenerationSettings, QwenExecutionOrchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Qwen3 plus Transformers execution scaffold.")
    parser.add_argument("--model-id", default=DEFAULT_QWEN_MODEL_ID, help="Hugging Face model identifier.")
    parser.add_argument("--prompt", required=True, help="User prompt to send to the model.")
    parser.add_argument("--system", default="You are a precise engineering assistant.", help="Optional system prompt.")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"], help="Torch device.")
    parser.add_argument("--torch-dtype", default="auto", help="Torch dtype or 'auto'.")
    parser.add_argument("--max-new-tokens", type=int, default=256, help="Maximum generated tokens per round.")
    parser.add_argument("--max-round-trips", type=int, default=4, help="Maximum execution round-trips.")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature.")
    parser.add_argument("--top-p", type=float, default=None, help="Top-p when sampling is enabled.")
    parser.add_argument("--do-sample", action="store_true", help="Enable sampling.")
    parser.add_argument("--enable-thinking", action="store_true", help="Enable Qwen thinking mode when supported.")
    parser.add_argument("--few-shot-example", action="store_true", help="Include one protocol demonstration exchange.")
    parser.add_argument(
        "--intercept-request-boundary",
        action="store_true",
        help="Stop generation as soon as </exec_request> is emitted and inject the runtime response immediately.",
    )
    parser.add_argument("--print-trace", action="store_true", help="Print the full execution conversation as JSON.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    orchestrator = QwenExecutionOrchestrator.from_pretrained(
        model_id=args.model_id,
        device=args.device,
        torch_dtype=args.torch_dtype,
    )
    messages = QwenExecutionOrchestrator.prepare_messages(
        args.prompt,
        system_prompt=args.system,
        include_protocol_example=args.few_shot_example,
    )
    result = orchestrator.run(
        messages,
        settings=GenerationSettings(
            max_new_tokens=args.max_new_tokens,
            do_sample=args.do_sample,
            temperature=args.temperature,
            top_p=args.top_p,
            enable_thinking=args.enable_thinking,
            intercept_request_boundary=args.intercept_request_boundary,
        ),
        max_round_trips=args.max_round_trips,
    )

    print(result.final_text)
    print()
    print(
        json.dumps(
            {
                "stop_reason": result.stop_reason,
                "used_execution": result.used_execution,
                "intercepted_requests": result.intercepted_requests,
                "structured_captures": result.structured_captures,
                "turns": len(result.turns),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if args.print_trace:
        print()
        print(json.dumps(result.messages, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
