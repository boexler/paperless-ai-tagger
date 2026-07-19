from typing import Literal

from app.config import Settings
from app.model_params import format_cursor_model_selection
from app.providers.base import AgentProvider
from app.providers.codex import CodexAgentProvider
from app.providers.cursor import CursorAgentProvider

AgentProviderName = Literal["cursor", "codex"]


def create_provider(settings: Settings) -> AgentProvider:
    """Create the configured agent provider implementation."""
    if settings.agent_provider == "codex":
        return CodexAgentProvider(settings)
    return CursorAgentProvider(settings)


def format_provider_model(settings: Settings) -> str:
    """Format provider and model settings for startup logging."""
    if settings.agent_provider == "codex":
        parts = [
            f"provider=codex model={settings.codex_model}",
            f"effort={settings.codex_reasoning_effort}",
        ]
        if settings.codex_model_verbosity:
            parts.append(f"verbosity={settings.codex_model_verbosity}")
        return " ".join(parts)

    model = format_cursor_model_selection(
        settings.cursor_model,
        settings.cursor_model_params,
    )
    return f"provider=cursor model={model}"
