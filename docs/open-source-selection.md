# Open-Source Model Selection

Date: 2026-03-17

## Decision

The primary open-source integration target is:

- model: `Qwen3-8B`
- framework: `Hugging Face Transformers`

Current implementation status:

- a first integration scaffold now exists in
  `src/llm_computer/qwen_transformers.py`
- details are documented in `docs/qwen-transformers-integration.md`

The planned scale-up path is:

1. `Qwen3-8B + Transformers`
2. `Qwen3-8B + SGLang`
3. `Qwen3-14B + the same integration path`
4. `vLLM` and `TensorRT-LLM` only after the execution lane contract is stable

## Selection criteria

The target model must satisfy the following requirements:

- dense decoder-only transformer rather than MoE
- open weights with permissive licensing
- official or first-party support in `Transformers`
- feasible runtime surgery for execution-mode attention and cache changes
- practical serving path after the research prototype

The target runtime must satisfy:

- minimal friction for a first integration
- debuggability against the current Python semantic reference
- a clear path toward production serving once the execution lane is stable

## Recommended model

### Primary recommendation: Qwen3-8B

Why it is the best first target:

- Qwen officially open-weights six dense Qwen3 models, including `Qwen3-8B`,
  under Apache 2.0.
- Qwen provides first-party examples for `Transformers`, `SGLang`, `vLLM`, and
  `TensorRT-LLM`, which lowers follow-on integration risk.
- Hugging Face already documents `Qwen3` as a native `Transformers` model
  family, so the first integration does not need a custom remote-code model.
- `8B` is large enough to be a credible planner model while still being small
  enough for repeated runtime experiments.

Why not start with a larger Qwen3 model:

- `Qwen3-14B` is a reasonable second step, but not the first one, because the
  execution-lane work is still architecture-first rather than capability-first.
- the MoE variants (`Qwen3-30B-A3B`, `Qwen3-235B-A22B`) introduce routing and
  KV-path complexity too early.

## Secondary candidates

### Qwen3-14B

Use it after the `8B` path is working:

- same family
- same basic integration story
- better planner headroom without changing the architectural assumptions

### Mistral NeMo 12B

This is the strongest fallback candidate:

- Apache 2.0
- standard architecture
- official claim that it is a drop-in replacement for systems using Mistral 7B
- strong fit for hardware-aware serving later on

It is not the first choice only because the current repository is already
leaning toward a Qwen-centered planning and serving path.

### Llama 3.1-8B

Use only as a baseline comparison:

- broad ecosystem support
- mature downstream tooling

It is not the preferred mainline target because:

- weight access is more gated
- licensing and download flow are more cumbersome than Qwen3
- it provides less iteration speed for this repository's immediate goals

## Models to defer

The following models should not be in the first integration batch:

- `Qwen3-30B-A3B`
- `Qwen3-235B-A22B`
- `Mixtral`-style MoE models
- `Llama 4`-style MoE or multimodal-first models
- non-transformer or hybrid-architecture models such as `Codestral Mamba`

Reason:

- they move the project away from the article's core transformer alignment
- they increase routing and runtime complexity before the execution lane itself
  is validated

## Recommended runtime sequence

### Stage 1: Transformers

Use `Transformers` first because:

- it is the lowest-friction environment for modifying model structure
- it is easiest to compare against the current semantic reference
- it does not require immediate serving-engine surgery

### Stage 2: SGLang

Use `SGLang` second because:

- it has an explicit path for adding new models
- it can fall back to `Transformers`
- its own guidance compares new model support against Hugging Face outputs and
  throughput baselines

This makes it the best bridge from research prototype to serving runtime.

### Stage 3: vLLM

Use `vLLM` only after the execution lane interface is stable:

- it offers a plugin system
- it is well-suited to higher-throughput serving
- but it is a worse place than `Transformers` for first-pass architecture work

### Stage 4: TensorRT-LLM

Use it only after the design is settled:

- it is valuable for NVIDIA-specific high-performance deployment
- it is not the right first environment for semantic debugging

## Final recommendation

The recommended baseline stack is:

- model: `Qwen3-8B`
- runtime: `Transformers`

The recommended second step is:

- same model family in `SGLang`

The recommended first comparison baseline is:

- `Llama 3.1-8B`

The recommended first scale-up is:

- `Qwen3-14B`

## Sources

- Qwen3 official blog: https://qwenlm.github.io/blog/qwen3/
- Qwen3 official repository: https://github.com/QwenLM/Qwen3
- Hugging Face Qwen3 documentation: https://huggingface.co/docs/transformers/model_doc/qwen3
- Hugging Face custom model documentation: https://huggingface.co/docs/transformers/en/custom_models
- SGLang support-new-models guide: https://docs.sglang.io/supported_models/support_new_models.html
- SGLang Transformers fallback guide: https://docs.sglang.io/supported_models/transformers_fallback.html
- vLLM plugin system: https://docs.vllm.ai/en/latest/design/plugin_system/
- Mistral NeMo announcement: https://mistral.ai/news/mistral-nemo
- Meta Llama models repository: https://github.com/meta-llama/llama-models
