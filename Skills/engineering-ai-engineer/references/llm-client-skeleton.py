"""LLM client wrapper — timeout, retry, structured output, cost logging.

Provider-agnostic shape; swap the call_provider() body for your SDK.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Type
from pydantic import BaseModel, ValidationError


log = logging.getLogger(__name__)


class ModelError(RuntimeError):
    """Raised when retries are exhausted or output is unparseable."""


async def _call_provider(
    *, model: str, system: str, user: str, max_tokens: int, timeout_s: float,
) -> tuple[str, int, int, float]:
    """Returns (text, in_tokens, out_tokens, cost_usd)."""
    # Replace with anthropic.AsyncAnthropic().messages.create / openai client, etc.
    raise NotImplementedError


async def call_model(
    *,
    model: str,
    system: str,
    user: str,
    schema: Type[BaseModel] | None = None,
    max_tokens: int = 1024,
    timeout_s: float = 30.0,
    max_retries: int = 2,
) -> tuple[BaseModel | str, dict]:
    """Returns (output, telemetry). Output is a validated pydantic model if `schema` given."""
    last_err: Exception | None = None

    for attempt in range(max_retries + 1):
        t0 = time.perf_counter()
        try:
            text, in_tok, out_tok, cost = await asyncio.wait_for(
                _call_provider(
                    model=model, system=system, user=user,
                    max_tokens=max_tokens, timeout_s=timeout_s,
                ),
                timeout=timeout_s + 1,
            )
        except (asyncio.TimeoutError, ConnectionError) as e:
            last_err = e
            await asyncio.sleep(2 ** attempt)
            continue

        telemetry = {
            "model": model,
            "in_tokens": in_tok,
            "out_tokens": out_tok,
            "cost_usd": cost,
            "latency_ms": (time.perf_counter() - t0) * 1000,
            "attempt": attempt,
        }
        log.info("llm_call", extra=telemetry)

        if schema is None:
            return text, telemetry

        try:
            return schema.model_validate_json(text), telemetry
        except ValidationError as e:
            last_err = e
            # Re-ask the model with the validation error appended.
            user = f"{user}\n\nYour previous response failed validation: {e}\nReturn ONLY valid JSON for the schema."

    raise ModelError(f"giving up after {max_retries + 1} attempts: {last_err}")
