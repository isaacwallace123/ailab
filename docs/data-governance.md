# Data Governance

## Data Classes

| Class | Examples | Indexing and use |
| :--- | :--- | :--- |
| Public | Portfolio text, public architecture diagrams | May use local or approved external models |
| Internal | Runbooks, topology, project notes, manifests | Local processing by default; scoped retrieval |
| Sensitive | Credentials, private prompts, raw logs, embeddings | Never commit; narrowly stored and never indexed by default |
| Cyber-sensitive | Exploit traces, packet captures, vulnerable endpoints | Remains in cyberlab unless sanitized and explicitly exported |

## Ingestion Rules

1. Collections and include patterns are allowlisted in `config/sources.*.yaml`.
2. Source roots are mounted read-only in the container.
3. Symlinks, path escapes, secret-like filenames, private/cache directories, unsupported file types,
   and oversized files are rejected before content processing.
4. Every chunk retains source provenance and a content hash.
5. Derived indexes must support deletion by source collection and content hash.
6. Adding a collection requires a documented owner, sensitivity, retention rule, and deletion path.

The implemented content scanner rejects private-key blocks, known provider token formats, and
high-entropy values assigned to credential-like fields. It records only the detector name and file
path, never the suspected value. This is defense in depth rather than proof that a document is safe;
provider-side scanning and repository secret scanning remain required.

## Memory Rules

Chat history and durable memory are separate.

- Conversations are retained according to an explicit retention setting.
- Conversations are not automatically promoted into personal memory.
- A user action may promote a conclusion into a note, decision, task, project fact, or preference.
- Durable memory entries record their source and may be reviewed, corrected, or deleted.

## External Provider Rules

- External providers are opt-in per model alias and data class.
- Sensitive and cyber-sensitive content cannot use an external model alias by default.
- Provider keys live in an approved secret store, never Git or application logs.
- Request logs redact authorization headers and known secret fields.

## Tool Safety

- Read and write credentials are separate.
- Read-only tools are the initial default.
- Write tools use narrow schemas, validation, idempotency where possible, and an audit event.
- Cross-lab or external mutations require user approval before execution.
- Retrieved text is untrusted input and cannot grant itself tool permissions.
