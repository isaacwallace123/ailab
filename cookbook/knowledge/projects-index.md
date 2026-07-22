# Projects Index

## Lab repositories

- `ailab` owns local model serving, LiteLLM, Open WebUI, retrieval, skills, tools, memory, and AI
  evaluation. Its active roadmap is `docs/roadmap.md`.
- `homelab` owns the k3s platform, GitOps applications, observability, storage, networking, and
  stable personal services.
- `cyberlab` owns Proxmox cyber-range infrastructure, isolated attacker and victim workloads,
  scenarios, schemas, and security exercises.
- `portfolio` owns public presentation. Only sanitized, intentionally public artifacts belong there.

## Application projects

Local application repositories include `BotProject`, `GamblingProject`, `Kleff`, and `portfolio`.
Treat each repository's README, architecture documentation, and working tree as authoritative before
assuming its purpose or current status. Remote GitHub metadata is useful for issues and pull requests,
but the local repository remains the implementation surface when it is available.

## Ownership rule

Make a change in the repository that owns the affected system. Cross-lab integrations use documented,
authenticated, read-only interfaces by default. Do not copy manifests or automation into the AI lab
merely to make them easier for an agent to access.
