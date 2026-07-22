---
name: improve-ai-cookbook
description: Turn repeated successful workflows, user corrections, bad answers, tool failures, and model benchmarks into versioned AI cookbook improvements. Use when capturing a reusable prompt or skill, adding an evaluation case, revising a model preset, or deciding whether a workflow belongs in knowledge, memory, a prompt, a skill, or a tool.
---

# Improve AI Cookbook

Classify the improvement before editing anything:

- Store stable facts and documents as knowledge.
- Store explicit user preferences, decisions, tasks, projects, or facts as reviewable memory.
- Store frequently invoked input templates as prompts.
- Store reusable judgment and workflow instructions as skills.
- Store deterministic computation or external access as tools.
- Store persona, bindings, and parameters as model presets.
- Store hardware fit and serving choices in the model catalog.

Then:

1. Capture the smallest reproducible example, expected behavior, actual behavior, and relevant evidence.
2. Add or update an evaluation case before changing a fragile prompt, retriever, router, or tool.
3. Make one focused change and record its version in Git.
4. Run syntax, schema, safety, and behavior validation. Compare against the previous baseline.
5. Promote only improvements that preserve citation validity, secret handling, access boundaries, and recovery behavior.
6. Never let the model silently rewrite its own production instructions or convert whole conversations into durable memory.
7. Keep failed experiments and measured results; remove secrets and private raw data before committing.
