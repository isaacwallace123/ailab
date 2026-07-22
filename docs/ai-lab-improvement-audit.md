# AI Lab Improvement Audit

## Outcome

The lab already has a strong infrastructure core: reproducible GPU workers, scoped LiteLLM routes,
an authenticated citation-first knowledge API, hybrid retrieval, read-only live-status connectors,
and a hardened Open WebUI deployment. The largest usability gap was that none of those capabilities
were packaged as a discoverable personal AI workspace. The versioned `cookbook/` and its Open WebUI
sync close that gap without inventing new model weights or weakening the existing trust boundaries.

Open WebUI models should be treated as role presets. The reusable architecture is:

```text
measured model weights -> LiteLLM routes -> role presets
                                      |-> knowledge collections
                                      |-> lazy-loaded skills
                                      |-> narrow read-only tools
                                      |-> evaluation cases and feedback
```

This separation lets one capable local model support many jobs while each role receives only the
context and capabilities it needs.

## Implemented In This Pass

- A Git-versioned model cookbook with hardware-fit evidence and promotion gates.
- Five Open WebUI role presets: general chat, lab operations, project work, evidence research, and
  family finance education.
- Three curated knowledge packs, six reusable prompts, six skills, and four narrow tools.
- Read-only access to the existing cross-lab retrieval/status API and allowlisted public GitHub repos.
- Deterministic finance calculations separated from model prose.
- Idempotent validation and Open WebUI synchronization scripts.
- Safety rules for evidence, prompt injection, repository scope, infrastructure changes, and finance.

## Highest-Priority Remaining Work

### P0: Recovery And Stable Access

- Reserve `.101` and `.102`, publish internal DNS/TLS for `.221`, and stop treating raw addresses as
  permanent product interfaces.
- Schedule VM and logical PostgreSQL backups, define retention and off-host copies, and perform a
  documented restore drill. A backup that has not been restored is only a hypothesis.
- Establish the first Git baseline for this currently uncommitted repository after reviewing secrets
  and generated artifacts. The code is reproducible only when its history actually exists.

### P0: Shared Tool Plane

- Publish the existing read-only assistant capabilities as an authenticated Streamable HTTP MCP
  server for Codex, Claude Code, Gemini, and Open WebUI.
- Keep credentials and network access in that isolated service. Open WebUI Workspace Tools execute
  Python inside the WebUI process, so their present wrappers must stay small, reviewed, and
  read-only.
- Add write tools only one at a time with preview, approval, audit, and recovery contracts.

### P1: Quality That Improves With Use

- Add answer-correctness, evidence-entailment, stale-data, adversarial retrieval, tool-selection,
  tool-argument, latency, and refusal cases. Store failures as regression fixtures.
- Add a reviewed feedback inbox for cookbook suggestions. Never let a chat silently rewrite its own
  production instructions or promote its own changes.
- Measure task success per role preset. Keep, change, or remove a skill based on observed outcomes,
  not prompt length or subjective cleverness.

### P1: Model And Routing Upgrades

- Benchmark the catalogued 14B candidate on correctness, tool calling, context pressure, recovery,
  and generation speed before promoting it. The current 8B route is fast, but complex multi-tool
  plans are the workload most likely to expose its limits.
- Evaluate a dedicated embedding and reranking pair only against the recorded hybrid baseline.
- Add capability-aware routing so casual chat, grounded answers, long-context work, and tool-heavy
  requests do not all pay the same latency and memory cost.

### P1: Observability

- Add OpenTelemetry/LLM traces for route selection, time to first token, total latency, tool calls,
  retrieval hit quality, citation validation, fallbacks, and errors. Redact prompts and secrets by
  default.
- Add node, container, queue, database, and GPU health metrics plus alerts tied to user-visible
  symptoms.

### P2: Broader Personal Workspace

- Configure a private search backend for the Researcher role; its web capability is useful only when
  Open WebUI has a reviewed search provider.
- Add portable project/decision/task notes and an explicit memory editor with provenance, expiry,
  conflict handling, and deletion.
- Add sanitized cyberlab status exports, then extend the Projects Index from curated summaries to a
  reviewed manifest of local and remote repositories.
- Add local speech only after chat, retrieval, and tool traces are observable and recoverable.

## Operating Rules

1. Keep facts in knowledge, behavior in skills, repeatable inputs in prompts, deterministic actions
   in tools, and runtime choice in the model catalog.
2. Prefer one strong base route with several scoped roles over downloading a different model for
   every personality.
3. Treat retrieved documents and repository content as untrusted data, never as instructions.
4. Default infrastructure and GitHub access to read-only and allowlisted.
5. Record every meaningful failure as an evaluation case before changing the system.
6. Promote candidates only after correctness, safety, latency, resource, and recovery gates pass.
