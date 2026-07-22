# Models

Model catalog and runtime notes.

Track documentation here:

- model name
- license
- source
- intended use
- hardware requirements
- quantization
- runtime
- evaluation notes

Do not commit large model files. Local model files should live under ignored paths such as `models/local/` or `models/cache/`.

## Pinned Smoke Model

The first runtime gate uses `Qwen/Qwen3-0.6B-GGUF` at repository revision
`23749fefcc72300e3a2ad315e1317431b06b590a`:

- file: `Qwen3-0.6B-Q8_0.gguf`
- size: 639,446,688 bytes
- SHA-256: `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`
- license: Apache-2.0
- purpose: hardware/runtime smoke testing only, not production model selection

Ansible stores it outside the repository under `/var/lib/ailab-runtime/models/smoke/` on the VM's
OS disk. The unformatted 500 GiB data disk remains untouched.

## First Realistic Candidate

The initial model-size benchmark uses `Qwen/Qwen3-8B-GGUF` revision
`7c41481f57cb95916b40956ab2f0b139b296d974`:

- file: `Qwen3-8B-Q4_K_M.gguf`
- size: 5,027,783,488 bytes
- SHA-256: `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`
- license: Apache-2.0
- purpose: realistic B50 performance, context, correctness, and stability evaluation

This candidate is evidence for runtime selection, not yet the permanent assistant model.
