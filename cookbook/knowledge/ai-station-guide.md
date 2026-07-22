# AI Station Guide

## Purpose

The AI station is a private, local-first intelligence layer for chat, project context, lab
operations, retrieval, model experiments, and carefully scoped external clients. Open WebUI is the
human chat surface, LiteLLM owns stable model routes and client limits, the Lab Status Assistant
owns citations and read-only lab policy, and the GPU workers run replaceable inference services.

## Choosing a model

- Use **Personal Assistant** for ordinary conversation and automatic lab-aware answers.
- Use **Lab Operator** for evidence-driven troubleshooting with read-only status tools.
- Use **Project Copilot** to orient across repositories and remote GitHub content.
- Use **Researcher** when a question depends on current external sources.
- Use **Family Finance Guide** for calm educational finance explanations and calculations.
- Use `ailab-grounded` directly when every factual lab claim must pass strict evidence validation.

Workspace models are presets over base routes; they are not additional trained weights.

## Evidence rules

Repository documentation can prove what was documented or intended. Terraform, Ansible, Compose,
and Kubernetes configuration can prove desired state. Only timestamped runtime connectors can prove
what is happening now. When evidence is stale, unavailable, or contradictory, report that state
instead of filling gaps from model memory.

## Tool rules

Infrastructure tools are read-only. They may search approved repository knowledge, obtain normalized
status, and ask the citation-validating assistant. They do not accept arbitrary shell commands,
PromQL, Proxmox paths, Kubernetes queries, or model names. Financial tools perform deterministic
math only and never access accounts or execute transactions.

## Improvement loop

Capture a real failure or correction, add the smallest reproducible evaluation, change one recipe
or subsystem, run validation, compare the measured result, and promote only when citations, secret
handling, latency, and recovery remain within their gates. Durable memory is explicit and reviewable;
entire conversations are never promoted automatically.
