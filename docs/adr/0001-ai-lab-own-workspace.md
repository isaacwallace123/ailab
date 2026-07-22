# ADR 0001: AI Lab Owns Its Own Workspace

## Status

Accepted

## Context

Isaac is splitting work across three related labs:

- homelab
- cyberlab
- ailab

Each lab needs a different focus and a different assistant workflow. The AI lab needs to develop local AI infrastructure and AI-powered operations without becoming tangled into the cyberlab or homelab repositories.

## Decision

Create `C:\Users\isaac\Desktop\ailab` as a standalone workspace for AI lab work.

The AI lab may integrate with the homelab, cyberlab, and portfolio through documented interfaces, but it does not own their core infrastructure.

## Consequences

The AI lab can move quickly on model serving, RAG, agents, evaluation, and demos.

Cross-lab dependencies must be documented. Changes to homelab, cyberlab, or portfolio resources should happen in those owning repositories.
