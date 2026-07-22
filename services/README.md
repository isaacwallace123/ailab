# Services

AI services, APIs, agents, notebooks, and demos.

Implemented services:

- [`lab-status-assistant`](lab-status-assistant/README.md)
- [`research-gateway`](research-gateway/README.md)

The model-serving platform services are deployed through Ansible rather than this source tree:
two hardened llama.cpp workers, loopback-only PostgreSQL, the scoped LiteLLM gateway documented in
[`docs/model-gateway.md`](../docs/model-gateway.md), and the chat surface documented in
[`docs/open-webui.md`](../docs/open-webui.md).

The Lab Status Assistant provides authenticated, allowlisted repository ingestion, citation-first
search, and read-only Prometheus, Kubernetes, ArgoCD, and Proxmox status. The Research Gateway
provides authenticated public-only retrieval, source provenance, and safe byte forwarding to the
private Docling extraction worker. Model-backed synthesis and MCP follow as separate source and
interface layers.
