# Datasets

Dataset documentation, manifests, and safe sample fixtures.

Before indexing or training on data, document:

- source
- permission level
- sensitivity
- retention rule
- deletion path
- whether embeddings may be generated

Do not commit private datasets, raw telemetry exports, embeddings, vector database files, or generated caches.

`retrieval-eval-v1.yaml` is the public-safe, versioned baseline used to measure lexical retrieval,
ranking, and citation integrity before an embedding model is selected. Run it against the deployed
PostgreSQL backend with `scripts/evaluate-retrieval.ps1`.
