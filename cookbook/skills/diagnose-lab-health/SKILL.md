---
name: diagnose-lab-health
description: Diagnose current health, availability, capacity, and configuration drift across the AI lab, homelab, cyberlab, Kubernetes, ArgoCD, Proxmox, model gateway, and AI services. Use for outages, warnings, status checks, capacity questions, or troubleshooting that must distinguish live runtime evidence from repository documentation.
---

# Diagnose Lab Health

1. Identify the lab, service, time window, and user-visible symptom.
2. Query the narrowest read-only runtime tool first. Check its observation timestamp and stale or unavailable state.
3. Search repository knowledge for intended architecture, ownership, recent decisions, and the relevant runbook.
4. Keep evidence types separate:
   - Runtime evidence supports claims about what is happening now.
   - Desired state explains what should exist.
   - Documentation explains decisions but does not prove health.
5. Correlate at least two signals when declaring a root cause. Otherwise label the result a hypothesis.
6. Report in this order: current state, evidence and timestamps, likely cause, safe next check, and recovery or escalation.
7. Never run remediation, shell commands, deployments, or infrastructure mutations through read-only tools.
8. If evidence is stale, missing, or contradictory, say so and request a fresh collection instead of guessing.

For cyberlab questions, never request a direct connection to attacker or victim networks. Use only approved sanitized status and documentation.
