# Local Inference Benchmark Plan

## Goal

Select the first supported local inference runtime using measured behavior on the Intel Arc Pro B50
16 GB and Intel Arc B580 12 GB rather than committing the platform to an untested runtime.

## Candidates

1. `llama.cpp` server with SYCL.
2. `llama.cpp` server with Vulkan.
3. vLLM with the Intel XPU backend after the baseline works.
4. Ollama Vulkan only as a convenience-layer experiment.

## Test Matrix

Use identical prompts, GGUF quantization where applicable, context sizes, and output limits.

| Dimension | Minimum cases |
| :--- | :--- |
| GPU | B50, B580 |
| Workload | chat, retrieval synthesis, tool call, structured JSON, code |
| Context | 4K, 16K, highest stable target |
| Concurrency | 1, 2, 4 clients |
| Model class | small baseline, primary 7B-14B class, larger/offloaded candidate |

## Measurements

- successful load and output correctness
- time to first token
- prompt-processing tokens per second
- generation tokens per second
- peak VRAM and system RAM
- long-context stability
- structured-output and tool-call validity
- concurrent throughput and latency
- recovery after service or driver restart
- idle and loaded power when metrics are available

## Selection Gate

The first runtime must complete the chat, retrieval, and structured-output suites without corrupted
output or unrecoverable GPU failures. Performance is evaluated only after correctness and stability.

Store sanitized results in `models/benchmarks/`; raw logs and model artifacts remain ignored.

## First Accepted Smoke Baseline

On 2026-07-18, pinned llama.cpp `b10066` at commit
`86a9c79f866799eb0e7e89c03578ccfbcc5d808e` successfully used `Vulkan0` on the Arc Pro B50 with
the checksum-pinned public `Qwen3-0.6B-Q8_0` smoke model. Three repetitions measured approximately
3,684.69 prompt tokens/s at 512 tokens and 68.74 generation tokens/s at 128 tokens. This proves the
build, model-load, full-offload, and compute path only; the small model is not a production-model
candidate and full answer-quality gates remain outstanding. Deterministic CLI and localhost-only
OpenAI-compatible API checks also returned their expected tokens. The API unit is disabled and
stopped after validation; no inference port is exposed on the VM network.

The first realistic candidate is official `Qwen3-8B-Q4_K_M`, pinned by repository revision and
SHA-256. With flash attention and all layers on `Vulkan0`, three repetitions measured approximately
505.32 prompt tokens/s at 512 tokens, 356.49 prompt tokens/s at 4K, and 16.11 generation tokens/s.
Its localhost API passed exact schema-constrained cluster-status JSON and a supplied-facts-only
Kubernetes answer containing the required `[source:k8s-snapshot]` citation. This is an initial pass;
long context, concurrency, tool calls, broader grounding quality, stability, and backend comparison
remain required before selection.

## B580 Comparison Baseline

On 2026-07-18, the identical llama.cpp commit, Vulkan settings, and checksum-pinned Qwen3 8B model
passed on `ai-node-02` with the Arc B580. It measured approximately 798.05 prompt tokens/s at 512
tokens, 552.57 prompt tokens/s at 4K, and 27.65 generation tokens/s. Exact structured JSON and
citation-grounding gates also passed. Against the B50 baseline, the B580 was about 1.55-1.72 times
faster in this matrix despite its smaller 12 GiB VRAM, supporting its `local-fast` worker role. The
B50 remains useful as `local-primary` for workloads needing its larger 16 GiB VRAM.
