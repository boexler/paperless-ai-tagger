"""OpenRouter chat client using the OpenAI-compatible API."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.config import Settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class OpenRouterClientError(Exception):
    """Raised when an OpenRouter chat request fails or returns invalid JSON."""


class OpenRouterClient:
    """Thin wrapper around OpenAI SDK pointed at OpenRouter."""

    def __init__(self, settings: Settings) -> None:
        headers: dict[str, str] = {}
        if settings.openrouter_http_referer:
            headers["HTTP-Referer"] = settings.openrouter_http_referer
        if settings.openrouter_app_name:
            headers["X-Title"] = settings.openrouter_app_name

        self.model = settings.openrouter_model
        self._client = OpenAI(
            api_key=settings.openrouter_api_key or "",
            base_url=settings.openrouter_base_url,
            default_headers=headers or None,
        )

    def complete_json(self, system_prompt: str, user_prompt: str, schema: type[T]) -> T:
        """Call the model and parse the assistant reply into a Pydantic schema."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
        except Exception as exc:
            raise OpenRouterClientError(f"OpenRouter request failed: {exc}") from exc

        content = ""
        if response.choices:
            message = response.choices[0].message
            content = (message.content or "").strip()

        if not content:
            raise OpenRouterClientError("OpenRouter returned an empty response")

        payload = _extract_json_object(content)
        try:
            return schema.model_validate(payload)
        except ValidationError as exc:
            raise OpenRouterClientError(f"Invalid JSON schema from model: {exc}") from exc


def _extract_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from raw model output, tolerating markdown fences."""
    candidate = text.strip()
    fence = _JSON_FENCE_RE.search(candidate)
    if fence:
        candidate = fence.group(1).strip()

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(candidate[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError as exc:
            raise OpenRouterClientError(f"Could not parse JSON from model output: {exc}") from exc

    raise OpenRouterClientError("Model output did not contain a JSON object")
