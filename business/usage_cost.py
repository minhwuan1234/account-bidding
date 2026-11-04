"""Summarize Responses API token usage and estimate text-token charges."""

from __future__ import annotations

from typing import Any


def summarize_usage(response: dict[str, Any]) -> dict[str, Any] | None:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return None
    try:
        input_tokens = max(0, int(usage["input_tokens"]))
        output_tokens = max(0, int(usage["output_tokens"]))
        details = usage.get("input_tokens_details") or {}
        cached_tokens = max(0, int(details.get("cached_tokens") or 0))
        cache_write_tokens = max(0, int(details.get("cache_write_tokens") or 0))
    except (KeyError, ValueError, TypeError):
        return None
    model = str(response.get("model") or "")
    cost_usd = None
    if model.startswith("gpt-6-luna") and response.get("service_tier") in (None, "default", "auto", "standard"):
        regular_tokens = max(0, input_tokens - cached_tokens - cache_write_tokens)
        input_multiplier = 2 if input_tokens > 272_000 else 1
        output_multiplier = 1.5 if input_tokens > 272_000 else 1
        cost_usd = (
            regular_tokens * 0.10 * input_multiplier
            + cached_tokens * 0.01 * input_multiplier
            + cache_write_tokens * 0.125 * input_multiplier
            + output_tokens * 0.50 * output_multiplier
        ) / 1_000_000
    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": cached_tokens,
        "cache_write_tokens": cache_write_tokens,
        "estimated_cost_usd": cost_usd,
    }
