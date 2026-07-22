# AI Lab Cookbook

This directory is the version-controlled source of truth for the AI Lab's reusable model recipes,
knowledge packs, prompts, skills, and tools. It provides the durable part of an Odysseus-style
workspace without replacing the existing Open WebUI, LiteLLM, retrieval, or GPU-worker stack.

The cookbook has two layers:

- `catalog/models.yaml` records measured routes, hardware fit, candidates, and promotion gates.
- `models/`, `knowledge/`, `prompts/`, `skills/`, and `tools/` define the Open WebUI experience.

Open WebUI models are configuration presets, not newly trained weights. Several presets can share
the same local base model while receiving different instructions, access boundaries, tools, skills,
knowledge, and generation parameters.

Shared presets use Open WebUI's runtime `{{USER_NAME}}` variable instead of hardcoded identities.
Display names come from each signed-in account, while durable assistant memories are isolated by the
authenticated Open WebUI user ID in the service layer.

## Included workspace

| Type | Included recipes |
| :--- | :--- |
| Models | Personal Assistant, Lab Operator, Project Copilot, Researcher, Family Finance Guide |
| Knowledge | AI Lab Operating Manual, Projects Index, Family Finance Foundations |
| Prompts | Lab/project operations, evidence and finance research, company fundamentals, finance scenarios, cookbook feedback |
| Skills | Lab/project operations plus evidence research, market interpretation, company fundamentals, scenario comparison, and personal finance |
| Tools | Lab and GitHub readers; controlled SearXNG search/public retrieval/OCR; finance search, calculator, planner, visualizer, official-data client, and optional market-data client |

## Workflow

1. Edit recipes in Git.
2. Run `python scripts/validate-cookbook.py`.
3. Preview model fit with `python scripts/model-cookbook.py recommend --task lab-ops`.
4. Preview an Open WebUI sync with `uv run python scripts/sync-openwebui-workspace.py --dry-run`.
5. Apply the reviewed sync. Existing cookbook-owned resources are updated in place; unrelated
   workspace resources are never deleted.
6. Add a regression case when a real answer or tool call fails, then improve one layer at a time.

Do not commit passwords, API tokens, model files, embeddings, private profiles, or exported chat
history. Tool credentials belong in Open WebUI Valves or the existing controller secret store.

The finance stack deliberately separates discovery, reading, official data, calculations, and
presentation. `finance_search.py` queries the private SearXNG instance, labels the output as search
discovery, and can send a selected result through the SSRF-resistant fetch/OCR gateway.
`official_finance_data.py` retrieves Bank of Canada series and SEC filings/facts; deterministic tools
perform planning arithmetic; and the visualizer renders only reviewed supplied values. The optional
`market_data.py` remains available for a future licensed feed, but Dad's Finance Guide does not depend
on Alpaca or present search-derived values as consolidated real-time quotes.

## Growing smarter safely

The lab improves through measured retrieval, better tools, explicit memory, curated knowledge, and
evaluation—not by allowing a model to silently rewrite its own production instructions. Capture
user corrections and failures as reproducible evaluation cases, version recipe changes in Git, and
promote them only after safety and quality gates pass.
