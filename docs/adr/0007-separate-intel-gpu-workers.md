# ADR 0007: Use Separate Intel GPU Worker VMs By Default

## Status

Accepted

## Context

The shared Proxmox host has an Arc Pro B50 with 16 GiB VRAM and an Arc B580 with 12 GiB VRAM.
Placing both cards in one VM could let selected runtimes split a model, but it couples maintenance,
reduces concurrent availability, and does not turn the cards into one transparent 28 GiB device.
Mixed-device multi-GPU behavior also remains runtime-specific and must be benchmarked.

## Decision

Assign the B50 to `ai-node-01` and the B580 to `ai-node-02`. Route requests by model alias and
workload so both workers can run concurrently. Keep dual-GPU, single-VM model splitting as a
controlled experiment for models that cannot fit one card; it is not the default production shape.

The initial fixed guest memory allocation is 32 GiB for `ai-node-01` and 16 GiB for `ai-node-02`,
leaving the shared host with substantially more capacity for cyberlab workloads.

## Consequences

Each GPU can be updated, benchmarked, restarted, and routed independently. The B50 remains the
larger-VRAM primary while the faster B580 is available for low-latency work, embeddings, voice,
background agents, and overflow. The two VMs still share one physical host and are not a physical
high-availability design.
