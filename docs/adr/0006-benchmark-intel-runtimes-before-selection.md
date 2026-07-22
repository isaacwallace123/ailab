# ADR 0006: Benchmark Intel Runtimes Before Selection

## Status

Accepted

## Context

The first AI host has Intel Arc Pro B50 and Arc B580 GPUs. Runtime support, stability, model formats,
and performance differ between SYCL, Vulkan, and Intel XPU implementations.

## Decision

Pass through one GPU first and execute the documented benchmark matrix before choosing the permanent
local model runtime. Begin with the B50 for its larger VRAM while keeping the B580 available for
comparison and rollback. Correctness and stability are selection gates before throughput.

## Consequences

Infrastructure code must not hard-code an unverified runtime. Benchmark evidence becomes a public-safe
portfolio artifact, while raw runtime logs and model files remain private and untracked.

