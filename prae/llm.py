"""Minimal LLM integration. One provider, one interface."""

import os
import json
from typing import Optional

try:
    import openai
except ImportError:
    openai = None  # type: ignore


def chat(
    messages: list[dict[str, str]],
    model: str = "gpt-4o",
    provider: str = "openai",
    api_base: Optional[str] = None,
    temperature: float = 0.7,
) -> str:
    """Send a chat completion request. Returns the assistant message content.

    Supports any OpenAI-compatible API via api_base.
    Falls back to a stub if the openai package is not installed.
    """
    if openai is None:
        raise RuntimeError(
            "openai package is required. Install it with: pip install openai"
        )

    kwargs: dict = {}

    api_key = os.environ.get("OPENAI_API_KEY", os.environ.get("PRAE_API_KEY", ""))

    if api_base:
        client = openai.OpenAI(api_key=api_key, base_url=api_base)
    else:
        client = openai.OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def chat_or_stub(
    messages: list[dict[str, str]],
    model: str = "gpt-4o",
    provider: str = "openai",
    api_base: Optional[str] = None,
    temperature: float = 0.7,
    dry_run: bool = False,
) -> str:
    """Like chat(), but returns a stub response in dry_run mode."""
    if dry_run:
        # Return a deterministic stub for testing
        role = ""
        for m in messages:
            if m["role"] != "system":
                continue
            content = m["content"].lower()
            # Check most specific patterns first
            if "pre-audit agent" in content:
                role = "pre_audit"
            elif "post-audit agent" in content:
                role = "post_audit"
            elif "rebut agent" in content:
                role = "rebut"
            elif "revise agent" in content:
                role = "revise"
            elif "propose agent" in content:
                role = "propose"

        if role == "propose":
            return json.dumps({
                "summary": "Stub proposal: adjust learning rate",
                "patch": "# No real changes in dry run mode",
                "expected_effect": "Slight improvement in loss",
                "success_criteria": "Loss decreases by >0.01",
            })
        elif role == "rebut":
            return json.dumps({
                "summary": "Stub rebuttal: proposal is reasonable",
                "concerns": [],
                "recommendation": "proceed",
            })
        elif role == "pre_audit":
            return json.dumps({
                "bounded": True,
                "only_mutable_surface": True,
                "success_criteria_defined": True,
                "rollback_path_exists": True,
                "worth_budget": True,
                "approve": True,
                "summary": "Stub pre-audit: approved",
            })
        elif role == "post_audit":
            return json.dumps({
                "metric_movement_meaningful": True,
                "matches_expected_mechanism": True,
                "narrative_laundering": False,
                "verdict": "keep",
                "summary": "Stub post-audit: keep",
            })
        elif role == "revise":
            return json.dumps({
                "summary": "Stub revision: tighter learning rate",
                "patch": "# No real changes in dry run mode",
                "expected_effect": "More targeted improvement",
                "success_criteria": "Loss decreases by >0.005",
            })
        else:
            return json.dumps({
                "summary": "Stub proposal: adjust learning rate",
                "patch": "# No real changes in dry run",
                "expected_effect": "Improve metric",
                "success_criteria": "Metric improves",
            })

    return chat(messages, model=model, provider=provider, api_base=api_base, temperature=temperature)
