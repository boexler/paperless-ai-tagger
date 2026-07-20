"""OpenRouter chat client using the OpenAI-compatible API."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.config import Settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
_EMPTY_RESPONSE_RETRIES = 3
_EMPTY_RESPONSE_BACKOFF_SECONDS = 2.0


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
            timeout=120.0,
        )

    def complete_json(self, system_prompt: str, user_prompt: str, schema: type[T]) -> T:
        """Call the model and parse the assistant reply into a Pydantic schema."""
        last_error: Exception | None = None
        for attempt in range(1, _EMPTY_RESPONSE_RETRIES + 1):
            try:
                content = self._create_completion(system_prompt, user_prompt)
                payload = _extract_json_object(content)
                return schema.model_validate(payload)
            except ValidationError as exc:
                raise OpenRouterClientError(f"Invalid JSON schema from model: {exc}") from exc
            except OpenRouterClientError as exc:
                last_error = exc
                if "empty response" not in str(exc).lower() or attempt >= _EMPTY_RESPONSE_RETRIES:
                    raise
                logger.warning(
                    "OpenRouter empty response (attempt %s/%s), retrying in %.1fs: %s",
                    attempt,
                    _EMPTY_RESPONSE_RETRIES,
                    _EMPTY_RESPONSE_BACKOFF_SECONDS,
                    exc,
                )
                time.sleep(_EMPTY_RESPONSE_BACKOFF_SECONDS)

        raise OpenRouterClientError(str(last_error) if last_error else "OpenRouter request failed")

    def _create_completion(self, system_prompt: str, user_prompt: str) -> str:
        """Send one chat completion and return non-empty assistant text."""
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

        if not response.choices:
            raise OpenRouterClientError(
                f"OpenRouter returned no choices (model={self.model})",
            )

        choice = response.choices[0]
        message = choice.message
        content = _message_text(message)
        if content:
            return content

        finish_reason = getattr(choice, "finish_reason", None)
        refusal = getattr(message, "refusal", None)
        raise OpenRouterClientError(
            "OpenRouter returned an empty response "
            f"(model={self.model}, finish_reason={finish_reason!r}, refusal={refusal!r})",
        )


def _message_text(message: Any) -> str:
    """Extract usable text from an OpenAI-compatible chat message."""
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()

    # Some reasoning models expose alternate text fields.
    for attr in ("reasoning", "reasoning_content"):
        value = getattr(message, attr, None)
        if isinstance(value, str) and value.strip():
            logger.info("Using message.%s as OpenRouter content fallback", attr)
            return value.strip()

    model_extra = getattr(message, "model_extra", None) or {}
    if isinstance(model_extra, dict):
        for key in ("reasoning", "reasoning_content"):
            value = model_extra.get(key)
            if isinstance(value, str) and value.strip():
                logger.info("Using model_extra.%s as OpenRouter content fallback", key)
                return value.strip()

    return ""


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
