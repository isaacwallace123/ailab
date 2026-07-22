# ADR 0004: Open API And MCP Contracts

## Status

Accepted

## Context

The AI station must serve a web UI, voice interface, Codex, Claude Code, Gemini, Cordly, and future
applications without coupling its knowledge or policy layer to a single client or model vendor.

## Decision

Expose three distinct interfaces:

- a versioned application API for orchestrated workflows
- an OpenAI-compatible gateway for model routing
- a Streamable HTTP MCP server for scoped agent resources and tools

All interfaces reuse the same authorization, data classification, retrieval, tool, citation, and
audit policies. Clients do not access raw databases or model runtimes directly.

## Consequences

Client UIs and model providers can change independently. The platform must maintain explicit schemas,
authentication scopes, and compatibility tests for each interface.

