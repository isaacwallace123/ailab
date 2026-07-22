# AI Lab Research Gateway

This service is the network-policy boundary between chat clients and the public web. It validates
and pins public DNS results, follows redirects manually, bounds response sizes and timeouts, strips
active HTML, and records retrieval provenance. Its extraction endpoint forwards validated bytes—not
URLs—to the private Docling service.

The authenticated `/v1/search` endpoint is the only supported programmatic path to the private
SearXNG JSON API. It accepts bounded query, category, language, recency, and result-count fields and
returns normalized result metadata. Search discovers sources; `/v1/fetch` and `/v1/extract` still
enforce public-destination and response policy before any result is read.

It deliberately does not render JavaScript. Dynamic-browser rendering belongs in a separate,
disposable worker whose only egress is an enforcing proxy; giving a general browser both direct LAN
access and chat-controlled navigation would defeat this gateway's SSRF boundary.
