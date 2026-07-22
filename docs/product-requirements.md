# AI Station Product Requirements

## Product Goal

Build a private, local-first AI station that provides one dependable intelligence layer for
personal assistance, project organization, lab operations, external coding agents, and application
integrations such as Cordly.

The station may route selected requests to external providers, but local services remain the default
for private knowledge and the system must continue to provide a useful offline mode.

## Primary Users And Clients

| Client | Primary need | Initial access |
| :--- | :--- | :--- |
| Isaac | Chat, voice, notes, project context, and lab summaries | Web UI and API |
| Codex, Claude Code, Gemini | Curated project context and lab knowledge | Read-only MCP |
| Cordly | Structured generation for Discord workflows | Scoped application API |
| Portfolio visitors | Evidence of the architecture and sanitized outputs | Static or mock data only |

## Required Capabilities

1. Answer questions over approved knowledge with file and line citations.
2. Distinguish declared configuration, repository documentation, and live runtime state.
3. Query timestamped read-only health sources for the homelab, cyberlab, and AI lab.
4. Support text chat, speech-to-text, and text-to-speech without making voice a separate brain.
5. Organize ideas, projects, decisions, tasks, and reference material in portable formats.
6. Expose authenticated, versioned APIs and an MCP server for external clients.
7. Route between local and explicitly configured external models through stable model aliases.
8. Trace retrieval, model calls, and tool calls without leaking secrets into telemetry.
9. Evaluate citation quality, retrieval quality, safety behavior, latency, and tool correctness.
10. Require explicit approval before mutating another lab or an external system.

## Non-Goals For The First Release

- Autonomous control of attacker, victim, firewall, Proxmox, Kubernetes, or Discord resources.
- Training or fine-tuning models before inference, retrieval, and evaluation are reliable.
- A dedicated Kubernetes cluster before multiple stable services justify it.
- Public access to private chat, model, vector database, agent, or orchestration endpoints.
- Treating all chat history as permanent personal memory.

## First Release Acceptance Criteria

- A search for an indexed subject returns at least one source path, line range, and content hash.
- Secret-like and non-allowlisted files do not enter the index.
- Repository status responses clearly state that they are not live infrastructure health.
- Production API requests require authentication.
- An unavailable source is reported without taking down available collections.
- Unit tests and linting pass from one documented validation command.
- The service runs locally and has a hardened, read-only container definition.

## Later Acceptance Criteria

- "How is my Kubernetes cluster doing?" uses live Prometheus and ArgoCD data with timestamps.
- "How is my cyberlab looking?" uses approved status exports without joining attacker/victim networks.
- Codex, Claude Code, and Gemini can retrieve the same scoped project context through MCP.
- Voice input and output use the same orchestrator, policies, citations, and memory rules as chat.
- Cordly generates a validated plan, shows a preview, and waits for approval before Discord changes.

