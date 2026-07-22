# ADR 0005: Portable Knowledge And Explicit Memory

## Status

Accepted

## Context

Personal notes and project knowledge must remain usable without a specific AI UI. Coding agents need
curated access, while embeddings, chat logs, and private memory require stricter lifecycle controls.

## Decision

Use Markdown plus metadata as the initial canonical knowledge format. Treat search indexes and
embeddings as derived data. Keep conversations separate from durable memory and require explicit
promotion into notes, decisions, tasks, project facts, or preferences.

PostgreSQL with pgvector is the planned durable metadata and retrieval store after the filesystem
MVP validates ingestion and citation behavior.

## Consequences

Knowledge stays portable and Git-friendly. The platform must implement provenance, reindexing,
deletion, sensitivity labels, and conflict-safe editing as the workspace grows.

