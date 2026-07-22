# Retrieval Evaluation

The AI lab uses a versioned retrieval suite before enabling embeddings or changing ranking logic.
The goal is to compare candidate retrieval systems against a known lexical baseline instead of
assuming that vector search improves operational questions.

## Version 1 Baseline

Recorded on 2026-07-18 against the deployed PostgreSQL full-text backend:

| Metric | Result | Required |
| :--- | ---: | ---: |
| Cases passed | 6 / 6 | 6 / 6 |
| Hit rate at configured K | 1.000 | 1.000 |
| Mean reciprocal rank | 0.833 | 0.550 |
| Citation validity | 1.000 | 1.000 |

Version 1 preserves six direct keyword cases spanning AI runtime selection, homelab GitOps,
cyberlab Windows/Packer work, Kubernetes placement policy, dataset governance, and Cordly's service
boundary.

## Version 2 Heading-Aware Gate

Version 2 is the active gate. It adds natural-language roadmap prioritization, reboot recovery,
model routing, live address inventory, NFS ownership, cyberlab orchestration, and isolation policy.
Each expected citation has an explicit maximum rank. Citation validity independently checks the
returned collection, path, line range, and SHA-256 against the current allowlisted index.

The July 18 expansion was prompted by a grounded-answer regression: a roadmap question retrieved
broad 120-line documents ahead of `docs/roadmap.md` and produced already-completed work as the next
priority. Markdown ingestion now splits on heading boundaries, ignores low-value query stop words,
boosts matching headings and filenames, and reranks PostgreSQL candidates with the same deterministic
lexical scorer used by the in-memory backend.

## Running The Evaluation

Start the Compose stack, then run:

```powershell
.\scripts\evaluate-retrieval.ps1
```

The command runs `datasets/retrieval-eval-v2.yaml` against the PostgreSQL backend and exits nonzero
when a case, citation-integrity check, or aggregate threshold fails.

## Embedding Selection Gate

A candidate embedding or hybrid search configuration should be evaluated using the same suite and
corpus. It should not replace the lexical backend unless it preserves citation validity and hit rate
while materially improving ranking across a larger, more adversarial evaluation set. Latency,
resource use, model license, offline availability, and deletion behavior must be recorded alongside
quality metrics.

Version the suite rather than rewriting historical expectations when the corpus or product questions
change. A new suite result should record its backend, corpus revision, configuration, and timestamp.
