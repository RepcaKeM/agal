---
name: engineering-ai-engineer
description: Build production AI features — LLM integration, RAG pipelines, eval harnesses, and inference endpoints. Use when adding an LLM-powered feature, designing a RAG/embeddings pipeline, writing model evals, picking between providers (OpenAI/Anthropic/local), or serving a model from an API.
---

# AI Engineer

## Overview

AI features fail in production for predictable reasons: no eval harness, no caching, no failure mode for "model says no", and prompt edits with no regression check. This skill enforces evals-first development and treats the model like any other unreliable dependency.

## When to Use

- Adding an LLM call to an application (chat, classify, extract, summarize, generate)
- Designing or modifying a RAG pipeline (chunking, embeddings, retrieval, re-ranking)
- Building or expanding an eval harness for prompt or model changes
- Choosing between providers (OpenAI / Anthropic / Cohere / Mistral / local via Ollama/vLLM)
- Serving a model via an API endpoint (real-time or batch)

## Iron Law

```
NO PROMPT OR MODEL CHANGE WITHOUT A REGRESSION RUN ON THE EVAL SET.

If you tweaked a prompt, swapped a model, changed the system message,
or modified retrieval — re-run evals and compare. "Looks better on
my one example" is how you ship regressions.

EVERY LLM CALL HAS: TIMEOUT · RETRY POLICY · FALLBACK BEHAVIOR ·
COST + LATENCY LOGGED.

The model is an unreliable network dependency. Treat it like one.
```

## Checklist (new LLM feature)

1. **Define the task contract**: what input, what output, what failure modes, what's "good enough". → check: written in one paragraph; a teammate could grade outputs from it.
2. **Build the eval set BEFORE iterating on the prompt** — 20–50 representative inputs with expected behavior (or grading rubric). → check: file in `evals/<feature>.jsonl`, committed.
3. **Pick the smallest model that passes the eval at acceptable cost+latency** — start with Haiku/Mini, escalate only when evals demand it. → check: cost-per-call + p95 latency documented.
4. **Add structured-output enforcement** — JSON mode, function calling, or schema-validated parsing with retry on invalid. → check: invalid outputs caught and either retried or surfaced as errors, never silently corrupted.
5. **Add observability** — log prompt hash, model, tokens in/out, latency, cost, traced via OTel. → check: a sample call appears in your trace UI with all fields.
6. **Add caching** — prompt-cache supported tokens (Anthropic / OpenAI), and result-cache where appropriate. → check: cache hit rate visible in metrics.
7. **Failure handling** — what does the app do when the model returns garbage, times out, or refuses? → check: explicit branch, not a 500.

## Checklist (RAG pipeline)

1. **Chunking strategy chosen for the content type** — semantic / fixed / sliding; not "default 1000 chars." → check: written reason; eval shows it beats default.
2. **Retrieval is evaluated separately from generation** — recall@k on a labelled set; you can fix retrieval without re-grading answers. → check: `evals/retrieval.jsonl` exists.
3. **Re-ranker considered for top-k > 5** — cross-encoder or LLM re-ranker. → check: ablated; included or excluded by data, not vibes.
4. **Citation / source attribution in the output** — caller can verify; you can debug. → check: every answer has source IDs.
5. **Embedding model + index versioned together** — switching either requires rebuild. → check: index manifest stores model name + version.

## Anti-Patterns

- **Prompt-tuning loop without evals.** "It works better now" is unmeasurable. You're trading silent regressions for visible improvements.
- **Mega-prompt with everything in the system message.** Costs tokens per call, hides which part matters. Split, eval, attribute.
- **Storing embeddings without the model version.** When you upgrade the embedder, you don't know which docs need re-encoding.
- **No timeout.** A hung LLM call ties up a worker indefinitely. Default 30s; surface as failure.
- **Logging full prompts AND outputs with PII unchecked.** GDPR violation + 6-month retention is forever. Redact or hash.
- **Picking a model based on a leaderboard.** Leaderboards are not your task. Eval on your data.
- **`temperature=0` because "deterministic"** — same model + same input still varies. Use seed if provider supports; assume non-determinism.
- **Streaming UI without backpressure or cancellation.** User closes tab → you keep paying tokens.

## When NOT to use an LLM

If a regex / classifier / SQL query / boolean rule solves the problem at 99% accuracy for $0.0001 — use that. LLMs are expensive, slow, and probabilistic. Reach for them when the problem is genuinely fuzzy: open-ended generation, semantic understanding, multi-step reasoning, or task variety that defeats hand-coding.

## Related skills

- [[engineering-data-engineer]] — for the data + feature pipelines that feed evals / retrieval
- [[engineering-backend-architect]] — when serving the model behind an API needs scale / contracts
- [[engineering-database-optimizer]] — vector store / pgvector / metadata index tuning

## References

- `references/eval-harness.py` — minimal eval runner (JSONL inputs + grader function + comparison report)
- `references/llm-client-skeleton.py` — wrapper with timeout, retry, structured output, cost logging
- `references/rag-pipeline.py` — chunk → embed → store → retrieve → rerank → answer with citations
- `references/provider-comparison.md` — when to pick Anthropic / OpenAI / local; pricing & latency notes
