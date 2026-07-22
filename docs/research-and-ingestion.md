# Research and Ingestion Plane

The research plane separates discovery, network access, extraction, evidence storage, and answer
generation. This separation keeps a useful internet-enabled assistant from turning every model or
document parser into an unrestricted network client.

## Deployed Services

| Service | Responsibility | Exposure |
| :--- | :--- | :--- |
| SearXNG | Search discovery and source diversity | `127.0.0.1:18888` only |
| Docling Serve | Local document, OCR, table, and structured-text extraction | `127.0.0.1:15001` with API key |
| Research Gateway | Public-only retrieval, provenance, and Docling byte forwarding | `127.0.0.1:18089` with API key |
| Open WebUI | User chat and bounded native web search | LAN allowlist on port `8080` |

SearXNG returns candidates; it does not make a source authoritative. Finance answers should prefer
regulators, issuer filings, central banks, exchanges, and entitled market-data feeds, then use web
search for corroboration and dated context.

Docling accepts file bytes only from trusted callers in this design. Although the upstream API
supports URL sources, its key is not given to chat models or browsers. The Research Gateway owns
remote retrieval and submits validated bytes to Docling.

## Controlled Fetch Contract

Before a gateway makes an HTTP request it must:

1. Accept only `http` and `https`, reject credentials in URLs, normalize the host, and enforce an
   explicit destination policy.
2. Resolve every destination and reject loopback, private, link-local, multicast, reserved, carrier-
   grade NAT, and cloud-instance metadata address ranges. Repeat resolution and validation for every
   redirect to reduce DNS rebinding and redirect-based SSRF.
3. Bound DNS, connect, first-byte, and total timeouts; redirect count; downloaded bytes; decompressed
   bytes; and concurrent requests per user.
4. Allow only reviewed content types. Stream to a temporary file while hashing; never load an
   unbounded response into memory.
5. Extract static HTML first. Use a browser renderer only for pages that require it, in a disposable
   container with no LAN route, no host mounts, a read-only filesystem, blocked downloads, and a
   short lifetime.
6. Record the requested URL, final URL, retrieval time, response metadata, SHA-256 digest, extraction
   method, and citations. Untrusted page text remains evidence, never system instructions.

The static retrieval and Docling-forwarding gateway is deployed. JavaScript browser rendering is the
next isolated slice: it must use a disposable worker whose only egress path is an enforcing proxy,
with no LAN route or host mounts. Until that worker exists, keep Open WebUI's current fetch limits and
destination filters enabled and do not expose the Docling API or its key to Workspace tools.

`ai-core-01` uses `1.1.1.1` and `9.9.9.9` for public DNS. The former router/ISP pair stopped resolving
public names after the AdGuard transition. This restores public research but does not replace a
future authoritative split-DNS service for private lab names.

## Personal Knowledge and Learning

The lab should become more useful through explicit, inspectable state rather than silently changing
model weights from conversations. Durable information belongs in versioned knowledge collections or
user-owned memory with source, timestamp, owner, sensitivity, and deletion/export controls.

Dad's portfolio should be a separate private collection and account boundary. Import manual holdings
or broker exports as normalized positions and transactions, keep raw files encrypted and out of Git,
attach market-data timestamps to valuations, and require confirmation before changing a holding.
Debate summaries from local, OpenAI, Claude, and Gemini models can be saved only after a synthesis
step records disagreements and supporting sources; model output by itself is not trusted knowledge.
