# Picking a provider — quick reference (eval on YOUR data before committing)

| Provider | Strengths | Watch out for |
|---|---|---|
| **Anthropic (Claude)** | Long context (200k+), strong reasoning, prompt caching (huge cost win for repeated system prompt), vision | No streaming-while-tool-use in some SDKs; output tokens cost more than input |
| **OpenAI (GPT)** | Broad ecosystem, structured outputs / function calling are mature, batch API for cheap async | Per-tier rate limits; "deprecation drift" — old models removed on schedule |
| **Cohere** | Strong reranker (Rerank API), multilingual embeddings | Smaller frontier model capability than Anthropic/OpenAI |
| **Mistral** | Open weights for some models, EU residency option | Capability gap vs frontier |
| **Local (Ollama / vLLM)** | Zero per-token cost, data stays on your hardware, latency control | GPU cost, ops burden; capability gap vs frontier; quantization quality varies |

## Decision shortcuts

- **Latency-sensitive UI** → smaller model (Haiku, Mini, Gemini Flash) first; only escalate if evals demand.
- **Long document understanding** → Anthropic Claude with prompt caching of the document.
- **Strict structured output** → OpenAI structured outputs OR Anthropic tool use; validate with Pydantic anyway.
- **Sensitive data, no cloud** → local (vLLM/Ollama), accept capability gap.
- **High-volume async** → OpenAI Batch API (50% discount, 24h SLA) or local.

## Prompt caching (Anthropic)
Cache the system prompt + long context block: 90% input-token cost reduction on cache hits, ~5 min TTL. Costs 25% more on the cache-write call. Net positive at >2 calls per cache TTL.

## Cost-watching habits

- Log `cost_usd` per call. Aggregate by feature + user. Set a budget alert.
- Compare `model × prompt-variant` cost vs eval score on the same eval set. Pareto-pick.
- Re-run cost analysis monthly — prices and model lineups change.
