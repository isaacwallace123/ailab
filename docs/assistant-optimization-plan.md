# Assistant Optimization Plan

## Current Measured Baseline

The July 18 live path now forwards genuine upstream SSE chunks from llama.cpp through LiteLLM, the
Lab Status Assistant, and Open WebUI. The accepted serving path is local to `ai-core-01`; the
workstation reverse bridge has been removed from production.

| Workload | Time to first content | Total time | Content chunks |
| :--- | ---: | ---: | ---: |
| Casual assistant, direct | 0.65 s | 3.32 s | 72 |
| Lab RAG, Open WebUI before context tuning | 2.42 s | 10.54 s | 209 |
| Lab RAG, Open WebUI after context and source tuning | 2.11 s | 8.89 s | 175 |

The retrieval v2 gate covers 14 questions with a 1.0 hit rate, 0.8929 MRR, and 1.0 citation
validity. All 578 approved chunks have BGE embeddings in PostgreSQL/pgvector. The main remaining
latency is prompt evaluation and generation, not vector search.

## Target Architecture

Do not create a VM for each application. The accepted CPU-only `ai-core-01` VM is the stable service
plane, while GPU workers remain replaceable.

- `ai-core-01`: Open WebUI, LiteLLM, Lab Status Assistant, PostgreSQL/pgvector, embedding and rerank
  services, memory, MCP, tracing, backups, and guarded internet tools.
- `ai-node-01` B50: quality-first model worker and candidate 14B route.
- `ai-node-02` B580: low-latency 8B worker, overflow, and optional accelerated reranking.
- Development workstation: management, evaluation, and development only; no required production
  tunnel or always-on assistant process.
- Homelab and cyberlab: read-only, authenticated integrations. Never attach the assistant service
  plane directly to cyber-range networks.

## Recommended Order

1. `ai-core-01` provisioning and the assistant/Open WebUI/LiteLLM/database migration are complete.
   Its address is static and the old services are retired with rollback data preserved. Schedule
   recurring backups, add off-host retention, and delete the old data only after the observation window.
2. Add request telemetry for retrieval time, model queue time, time to first token, prompt tokens,
   cached tokens, generation tokens per second, selected route, and citation validation.
3. Benchmark llama.cpp prompt cache reuse and draftless n-gram speculative decoding independently.
   Keep a change only when correctness gates remain green and p50/p95 latency improves.
4. Benchmark an official Qwen3 14B Q4 model on the B50 as `local-smart`; retain Qwen3 8B on the B580
   as `local-fast`. Route ordinary chat to fast and difficult synthesis/coding to smart based on an
   explicit intent and quality policy, not prompt length alone.
5. Compare the current BGE-small hybrid baseline with Qwen3-Embedding-0.6B and
   Qwen3-Reranker-0.6B. Rerank only a bounded top candidate set and require the retrieval suite plus
   semantic-only cases to improve before switching defaults.
6. Publish authenticated read-only Streamable HTTP MCP tools for knowledge, documents, lab status,
   projects, and memory so Codex and Claude Code receive the same context as Open WebUI.
7. Add guarded internet research as a tool: search, fetch, sanitize, cite, cache, and enforce egress
   policy. Internet text is untrusted evidence and never grants tool permission.
8. Expand explicit memory with semantic retrieval, edit/delete UI, conflict handling, provenance,
   and retention. Never automatically promote entire conversations into durable memory.

## Near-Term Quality Work

- Add answer correctness and evidence-entailment evaluation, not only retrieval and citation shape.
- Add exact real-user prompts when a bad answer appears; the `personal-next-work` case is the first
  example of this feedback loop.
- Add source authority and lifecycle metadata so canonical roadmaps outrank snapshots and stale
  handoffs without relying on path-specific rules.
- Refresh changed documents incrementally instead of only at service startup.
- Stream `ailab-assistant` optimistically while retaining `ailab-grounded` as the buffered,
  citation-validated mode for strict evidence workflows.

## Performance Guardrails

- Casual p50 time to first token: under 1 second.
- Grounded p50 time to first token: under 2 seconds after `ai-core-01` removes the workstation tunnel.
- Default answer: under 250 words unless the user requests depth.
- Retrieval: under 150 ms p95 for the current corpus.
- No model/runtime change ships without deterministic format, retrieval, citation, and recovery gates.

## Primary References

- Qwen3 Embedding and Reranker: <https://qwenlm.github.io/blog/qwen3-embedding/>
- Official Qwen3 14B GGUF: <https://huggingface.co/Qwen/Qwen3-14B-GGUF>
- llama.cpp server caching, metrics, streaming, reranking, and tool support:
  <https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md>
- llama.cpp speculative decoding:
  <https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md>
