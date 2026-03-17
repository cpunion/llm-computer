# 我们如何用 5 种方式让 LLM 执行程序

![Animated overview](assets/five-implementation-overview.gif)

## 原文参考

这篇项目文章是基于 Percepta 原文所做的实现与验证报告：[Can LLMs Be Computers?](https://www.percepta.ai/blog/can-llms-be-computers)

- 原文标题：*Can LLMs Be Computers?*
- 原文副标题：Executing programs inside transformers with exponentially faster inference
- 发布方：Christos Tzamos 等，Percepta
- 发布时间：2026-03-11
- 原文链接：https://www.percepta.ai/blog/can-llms-be-computers

## TL;DR

现在这个仓库里已经有 5 条可运行的执行路径，从最浅的语义基线一路到当前最深的开源集成。这个“梯子”要表达的重点，不是越深的实现已经一定越快，而是每深入一层，程序执行的边界都会更靠近模型本体，同时保持同一份底层 WASM 执行契约。

本次 live comparison 使用：

- 开源路径：`Qwen/Qwen2.5-0.5B-Instruct`
- 闭源路径：`gemini-3-flash-preview`
- 设备：`mps`

在统一的 canonical WASM 场景下，5 种方式都返回了相同的最终结果 `42`。

![Implementation ladder](assets/five-implementation-ladder.png)

## 为什么这条梯子重要

很多关于 tool use 和 in-model execution 的讨论，把太多设计层级压缩成了一个问题。实际工程里，它们是几种清晰不同的集成层：

1. 先有一个定义“什么叫执行正确”的语义基线。
2. 再有一个已经使用 append-only 状态恢复的机制基线。
3. 再往上是只能通过 sidecar 调用的闭源模型路径。
4. 然后是能在本地 runtime 中截获结构化请求的开源 wrapper 路径。
5. 最深的一层，是去掉文本往返、开始接近原文“内生执行器”形态的开源 execution block。

真正有价值的地方在于：这个仓库现在已经能用同一套 service contract、同一套 article examples，把这 5 层都跑通并对齐到同一个语义参考。

![Execution boundaries](assets/five-implementation-paths.png)

## 五种实现

### 1. Reference Direct

这是最干净的语义基线：解析 WASM，用普通可变状态执行程序，不经过任何模型编排，直接返回结果。

**执行边界。** service 直接调用 reference WASM executor。

**Canonical 6 × 7 结果。** 端到端 `30.85 ms`，最终值 `42`。

**实现方式**

- 使用 `ReferenceWasmExecutor` 作为语义真值参考。
- 完全绕过 prompt protocol、wrapper 和 tool call。
- 定义了后续所有更深实现都必须保持一致的 trace 语义。

**测试情况**

- 已通过 five-way comparison，最终结果为 `42`。
- 已完整验证 Hungarian，结果为 `206`。
- 已完整验证原文 Sudoku，checksum 为 `1276684605`，总步数 `22,370,167`。

### 2. Append-Only Naive Direct

这是第一条真正与原文机制对齐的执行路径：程序状态不再用普通可变 locals / stack 保存，而是通过 append-only writes 重建；但状态检索仍然是 naive timeline scan，还没有用几何加速。

**执行边界。** service 调用 append-only executor，并使用 naive timeline scan。

**Canonical 6 × 7 结果。** 端到端 `17.52 ms`，最终值 `42`。

**实现方式**

- 把 locals 和 stack 改成 append-only state timelines。
- 保持与其他 direct backend 相同的请求/响应边界。
- 作为 hull 几何检索是否真的有价值的对照组。

**测试情况**

- 已通过 five-way comparison，最终结果为 `42`。
- 已完整验证 Hungarian，结果为 `206`。
- 已与 reference 对齐到 Sudoku `10,000` steps 的 prefix state。

### 3. Closed-Source Sidecar

这是闭源权重 API 下最现实的路径：模型仍然是 planner，而真正的执行通过严格定义的 tool schema 和共享 sidecar service 完成。

**执行边界。** Gemini 负责规划，sidecar 负责执行，Gemini 再输出最终答案。

**Canonical 6 × 7 结果。** 端到端 `4.115 s`，最终值 `42`。

**实现方式**

- 使用 `gemini-3-flash-preview` 并强制 tool use。
- 执行 backend 与开源路径共享。
- 因为拿不到 runtime internals，无法把执行真正移入模型权重内部。

**测试情况**

- 已通过 five-way comparison，最终结果为 `42`。
- live validation 中记录到 `tool_calls=1`。
- 由 Gemini integration tests 以及 stage 3、stage 10 共同覆盖。

### 4. Open-Source Wrapper

这条路径仍然把执行放在模型块图之外，但已经把 orchestration 推进到开源 runtime 内部：请求提取、structured capture、response injection 都在本地 runtime 中完成。

**执行边界。** Qwen 先输出结构化 execution request，runtime 解析执行后再回填 response span。

**Canonical 6 × 7 结果。** 端到端 `1.178 s`，最终值 `42`。

**实现方式**

- 基于 `Transformers` 对 `Qwen/Qwen2.5-0.5B-Instruct` 做验证。
- 支持 tagged request、structured capture 和 prefilled structured prompt mode。
- 仍然需要一次 runtime feedback 往返，还不是 native execution block。

**测试情况**

- 已通过 five-way comparison，最终结果为 `42`。
- 记录到 `intercepted_requests=1` 和 `structured_captures=1`。
- 由 stage 4 到 stage 8 以及 comparison harness 覆盖。

### 5. Open-Source Execution Block

这是当前最深的一层开源集成：模型生成仍在环内，但执行往返已经不再依赖 wrapper-only 的文本协议，而是走 native execution-block 路径。

**执行边界。** Qwen 仍然输出请求，但 runtime 会原生解析并返回紧凑的 execution feedback，而不是再喂回一段 `exec_response` 文本。

**Canonical 6 × 7 结果。** 端到端 `857.05 ms`，最终值 `42`。

**实现方式**

- native execution round 固定使用 `transformer_hull` backend。
- 把 `exec_response` 文本回路从 hot path 中移除。
- 是从今天的 wrapper 集成走向未来真正“模型内 execution heads”的桥梁。

**测试情况**

- 已通过 five-way comparison，最终结果为 `42`。
- 记录到 `native_execution_rounds=1`，且没有 runtime answer fallback。
- 由 stage 9、comparison harness 和 transformer regression suite 覆盖。

## 对比快照

![Latency chart](assets/five-implementation-latency.png)

| 深度 | 方法 | 类别 | 端到端耗时 | 是否实际执行 | 关键运行时信号 |
| ---: | --- | --- | ---: | --- | --- |
| 1 | Reference Direct | direct | 30.85 ms | yes | - |
| 2 | Append-Only Naive Direct | direct | 17.52 ms | yes | - |
| 3 | Closed-Source Sidecar | closed source | 4.115 s | yes | tool_calls=1 |
| 4 | Open-Source Wrapper | open source | 1.178 s | yes | structured_captures=1 |
| 5 | Open-Source Execution Block | open source | 857.05 ms | yes | native_execution_rounds=1 |

## 原文例子带来了什么

原始仓库一开始已经能处理 toy arithmetic 和一些小型 compiled-C 示例。但新的要求更高：必须把 Percepta 原文真正展示给读者的例子也验证进来。这一步直接抬高了整个项目的可信度门槛。

![Article examples](assets/article-example-results.png)

现在，原文中的 Hungarian 例子已经能在 4 条本地 backend 上得到相同结果 `206`；原文中的 Sudoku 题面，也已经能在 reference WASM executor 下完整跑到 checksum `1276684605`。

Sudoku 这部分尤其重要，因为它把两个经常被混在一起的说法拆开了：

- semantic reference executor 下的 full-result correctness
- append-only / transformer-style 路径下的 prefix-state equivalence

这样写法更诚实：这个长题目已经在仓库里完整求解，但当前被作为保留验证产物完整跑到底的，仍然只有 reference 路径。

![Sudoku prefix validation](assets/sudoku-prefix-validation.png)

## 每一层各自说明了什么

- reference 路径仍然不可替代。它是唯一干净的语义正确性基准。
- append-only naive 证明了原文机制不只是一个优化技巧。状态确实可以通过 append-only writes 重建。
- closed-source sidecar 证明了闭源 API 也能接入，但前提是接受硬工具边界。
- open-source wrapper 证明了即使不改模型权重，也能把普通本地模型变成 execution-aware system。
- open-source execution-block 是当前最接近原文终态的路径，因为它已经去掉了文本响应回路，开始呈现 native execution lane 的形态。

## 验证矩阵

![Validation matrix](assets/five-implementation-validation-matrix.png)

## 最终总结

现在这个仓库里有 5 种不同的执行实现，它们都能返回同一个 canonical answer，但背后的架构承诺完全不同。实现越深，程序执行离模型边界越近；例子越难，就越需要保留独立的验证产物，而不是把所有东西都压成一句营销式结论。

因此，目前最准确、最有用的结论，不是夸张宣传，而是下面这句：

> 我们现在已经能在同一个代码库中对比 5 层具体执行路径，用同一个语义真值参考去校验它们，并证明原文里的 Hungarian 和 Sudoku 例子都能沿着这条实现梯子被保留下来，而不只是停留在玩具算术上。

目前仍然存在的差距也很清楚：真正插进真实开源模型内部的 execution-head 路径，还需要替换掉最后那层确定性的 Python transition layer。

## 相关文件

- 原文链接：https://www.percepta.ai/blog/can-llms-be-computers
- `docs/five-way-comparison.json`
- `docs/article-example-validation.json`
- `docs/sudoku-result-validation.json`
- `docs/stage-validation-log.md`
