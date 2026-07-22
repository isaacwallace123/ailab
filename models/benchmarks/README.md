# Runtime Benchmark Evidence

This directory contains sanitized, public-safe benchmark summaries. Model weights, raw logs,
prompts containing private context, addresses, and credentials must never be committed.

The first artifact validates the B50 and llama.cpp Vulkan execution path with a small public model.
It is a runtime smoke test, not evidence that the model is suitable for the assistant.

Later runtime comparisons must use the matrix in `docs/runtime-benchmark-plan.md` and record:

- exact runtime release and source commit
- exact model revision, file checksum, quantization, and license
- hardware, kernel, backend, offload, context, and concurrency
- prompt-processing and generation performance with repeat counts
- correctness, structured-output, stability, and recovery results
- known warnings or failed cases
