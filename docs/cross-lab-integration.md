# Cross-Lab Integration

## Goal

The three labs should be different projects with clean communication paths.

They should integrate through documented interfaces:

- dashboards
- metrics
- logs
- read-only APIs
- exported reports
- sanitized docs
- portfolio pages

They should not integrate through hidden manual dependencies or copied state.

## Ownership

| Area | Owner |
| :--- | :--- |
| Homelab k3s platform | `homelab` |
| Cyber range VMs and scenarios | `cyberlab` |
| AI runtimes, agents, RAG, evals | `ailab` |
| Public presentation | `portfolio` |

Physical hosts are temporarily shared, but ownership follows the repository. An AI VM may run on
the `cyberlab` node without becoming cyberlab infrastructure. Homelab observability may display AI
or cyberlab health without managing those resources.

## Communication Pattern

Recommended flow:

```text
homelab metrics/logs/status
          |
          v
     approved APIs
          |
          v
ailab lab-status assistant <--- sanitized cyberlab docs/reports
          |
          v
portfolio-safe summaries
```

The AI lab can summarize, explain, and automate. It should not silently mutate another lab.

## Integration Ideas

### Homelab To AI Lab

- Prometheus read-only queries for service health — first runtime connector implemented
- Grafana dashboard links
- Kubernetes object status and ArgoCD Application exports — implemented through a minimized snapshot
- Homepage service metadata
- Loki logs only for approved namespaces

The current connector endpoint is configuration, not a durable contract. Local discovery confirmed
Prometheus at the manifest-declared direct LoadBalancer address, while other repository documentation
still assigns that address to a different service. Keep the URL in the ignored `.env` until the
homelab repository reconciles its address inventory. The connector never exposes arbitrary PromQL.

The Kubernetes/ArgoCD connector reads only nodes, pods, Deployments, StatefulSets, DaemonSets, and
ArgoCD Applications through the existing host kubectl identity. It normalizes status before writing
the ignored snapshot, caps historical Failed-pod examples, and never copies cluster credentials into
Docker. kube-state-metrics is not currently deployed, so Kubernetes object health comes from this
snapshot rather than invented Prometheus signals.

### Cyberlab To AI Lab

- Read-only scenario definitions
- Exercise reports
- Wazuh alert summaries
- Packet capture metadata, not raw sensitive captures by default
- Sanitized incident timelines
- Detection engineering notes

### AI Lab To Cyberlab

- SOC alert explanation
- Attack timeline summarization
- Detection rule draft generation
- Report generation
- Scenario documentation assistance

Any AI-generated security recommendation must be reviewed before it changes firewall policy, detection rules, vulnerable services, or attacker tooling.

### AI Lab To Portfolio

- Static architecture diagrams
- public-safe lab summaries
- demo screenshots
- writeups without secrets, private IPs where unnecessary, or vulnerable endpoint exposure

## Shared Observability

Use the homelab observability stack as the first shared view:

- Prometheus for metrics
- Grafana for dashboards
- Loki for logs
- Alertmanager and ntfy for notifications

AI lab and cyberlab can export into this system without being managed by the homelab repo.

## First Integration Contract

For `lab-status-assistant`, start with file-based, read-only ingestion:

| Source | Allowed early inputs | Exclusions |
| :--- | :--- | :--- |
| `ailab` | README, docs, ADRs, service docs, model docs | `.env`, caches, model files, generated vector DBs |
| `homelab` | README, docs, selected manifests, Backstage catalog | sealed secrets, private media metadata, tokens |
| `cyberlab` | README, docs, ADRs, scenario schemas, sanitized reports | raw packet captures, exploit payloads, vault files, private keys, attacker notes not marked for indexing |

Every answer should cite source files. Any future action that mutates another lab must be a
separate reviewed interface, not a hidden tool path from the AI assistant.
