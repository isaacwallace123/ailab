---
name: navigate-projects
description: Orient across local repositories and projects by finding ownership, architecture, source-of-truth files, implementation locations, current status, and next work. Use when asked where something lives, how repositories relate, what a project does, what to work on next, or which repo should own a change.
---

# Navigate Projects

1. Search across the smallest relevant collection set, then widen only if needed.
2. Prefer source-of-truth files in this order: active roadmap or issue, architecture and ADRs, deployment configuration, implementation, handoff notes, then generated artifacts.
3. Identify the owning repository before recommending a change. Do not copy implementation across lab boundaries.
4. Distinguish current implementation from future plans and stale handoff text.
5. Cite repository, relative path, and line range for every project-specific conclusion.
6. Summarize orientation as: purpose, owner, important paths, runtime/deployment shape, current state, and the next concrete task.
7. When asked to modify code, inspect local instructions and the working tree before proposing edits.

Use repository knowledge for discovery. Use the GitHub reader only for remote repository metadata, issues, pull requests, or content that is not present locally.
