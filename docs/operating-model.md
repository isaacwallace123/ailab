# Operating Model

## Principle

Manage the three labs as a small platform ecosystem:

- separate repos
- separate ownership boundaries
- shared conventions
- shared observability
- documented integration contracts

## Recommended Tools

| Need | Tooling |
| :--- | :--- |
| VM lifecycle | Proxmox plus Terraform |
| Host configuration | Ansible |
| Stable services | k3s plus ArgoCD where useful |
| Secrets | Ansible Vault, Sealed Secrets, or external secret store depending on runtime |
| Monitoring | Prometheus, Grafana, Loki, Alertmanager |
| Remote access | Tailscale and internal DNS |
| Public presentation | Portfolio site with sanitized data |

## Efficient Management

Use one dashboard layer, not one repo.

Recommended dashboards:

- Homelab platform health
- Cyberlab range health
- AI lab service health
- Cross-lab roadmap/status
- Public portfolio readiness

Recommended repo docs:

- `README.md` for current state
- `docs/architecture.md` for system shape
- `docs/roadmap.md` for next phases
- `docs/security-boundaries.md` for rules
- `docs/adr/` for decisions
- `HANDOFF.md` for the assigned assistant context

## Cross-Lab Change Rule

When a change affects another lab:

1. Make the implementation change in the owning repo.
2. Update integration docs in both repos if needed.
3. Keep generated exports out of Git unless they are sanitized and intentionally tracked.
4. Reflect public-facing changes in the portfolio repo.

## Near-Term AI Lab Workflow

1. Build locally in `services/`.
2. Document runtime assumptions in `docs/`.
3. Add scripts for repeatable validation.
4. Promote stable services to `kubernetes/` or `ansible/`.
5. Add metrics/logging before treating a service as permanent.
