from typing import Literal

from app.config import Settings
from app.model_params import format_cursor_model_selection
from app.providers.base import AgentProvider
from app.providers.codex import CodexAgentProvider
from app.providers.cursor import CursorAgentProvider
from app.providers.openrouter import OpenRouterAgentProvider

AgentProviderName = Literal["cursor", "codex", "openrouter"]


def create_provider(settings: Settings) -> AgentProvider:
    """Create the configured agent provider implementation."""
    if settings.agent_provider == "codex":
        return CodexAgentProvider(settings)
    if settings.agent_provider == "openrouter":
        return OpenRouterAgentProvider(settings)
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

    if settings.agent_provider == "openrouter":
        parts = [
            f"provider=openrouter model={settings.openrouter_model}",
            f"base_url={settings.openrouter_base_url}",
        ]
        if settings.openrouter_confidential_model:
            parts.append(
                f"confidential_model={settings.openrouter_confidential_model}",
            )
            providers = settings.parsed_confidential_providers()
            if providers:
                parts.append(f"confidential_providers={','.join(providers)}")
        return " ".join(parts)

    model = format_cursor_model_selection(
        settings.cursor_model,
        settings.cursor_model_params,
    )
    return f"provider=cursor model={model}"
