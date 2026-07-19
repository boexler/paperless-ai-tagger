import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from app.codex_config import build_codex_config_content
from app.config import Settings
from app.providers.codex import CodexAgentProvider
from app.providers.factory import create_provider, format_provider_model


def _env(**values: str) -> dict[str, str]:
    """Build a minimal environment for Settings initialization."""
    base = {
        "WEBHOOK_SECRET": "secret",
        "PAPERLESS_BASE_URL": "http://paperless:8000",
        "PAPERLESS_API_TOKEN": "token",
    }
    base.update(values)
    return base


class SettingsValidationTests(unittest.TestCase):
    """Validate provider-specific settings rules."""

    def test_cursor_provider_requires_cursor_api_key(self) -> None:
        with patch.dict(os.environ, _env(AGENT_PROVIDER="cursor"), clear=True):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)

    def test_codex_provider_requires_codex_api_key(self) -> None:
        with patch.dict(os.environ, _env(AGENT_PROVIDER="codex"), clear=True):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)

    def test_codex_provider_accepts_codex_api_key(self) -> None:
        with patch.dict(
            os.environ,
            _env(AGENT_PROVIDER="codex", CODEX_API_KEY="sk-test"),
            clear=True,
        ):
            settings = Settings(_env_file=None)
            self.assertEqual(settings.agent_provider, "codex")

    def test_invalid_codex_reasoning_effort_is_rejected(self) -> None:
        with patch.dict(
            os.environ,
            _env(
                AGENT_PROVIDER="codex",
                CODEX_API_KEY="sk-test",
                CODEX_REASONING_EFFORT="turbo",
            ),
            clear=True,
        ):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)


class CodexConfigTests(unittest.TestCase):
    """Validate generated Codex config content."""

    def test_build_codex_config_contains_paperless_mcp(self) -> None:
        with patch.dict(
            os.environ,
            _env(
                AGENT_PROVIDER="codex",
                CODEX_API_KEY="sk-test",
                PAPERLESS_API_TOKEN="paperless-token",
                CODEX_MODEL="gpt-5.4-mini",
                CODEX_REASONING_EFFORT="low",
            ),
            clear=True,
        ):
            settings = Settings(_env_file=None)
            content = build_codex_config_content(settings)

        self.assertIn('model = "gpt-5.4-mini"', content)
        self.assertIn('model_reasoning_effort = "low"', content)
        self.assertIn("[mcp_servers.paperless]", content)
        self.assertIn('PAPERLESS_URL = "http://paperless:8000"', content)
        self.assertIn('PAPERLESS_TOKEN = "paperless-token"', content)
        self.assertIn("network_access = true", content)


class ProviderFactoryTests(unittest.TestCase):
    """Validate provider factory selection."""

    def test_create_cursor_provider_by_default(self) -> None:
        with patch.dict(
            os.environ,
            _env(CURSOR_API_KEY="cursor-test"),
            clear=True,
        ):
            settings = Settings(_env_file=None)
            provider = create_provider(settings)
        self.assertEqual(provider.__class__.__name__, "CursorAgentProvider")

    def test_create_codex_provider_when_configured(self) -> None:
        codex_home = str(Path(tempfile.gettempdir()) / "codex-test")
        with patch.dict(
            os.environ,
            _env(
                AGENT_PROVIDER="codex",
                CODEX_API_KEY="sk-test",
                CODEX_HOME=codex_home,
            ),
            clear=True,
        ):
            settings = Settings(_env_file=None)
            provider = create_provider(settings)
        self.assertEqual(provider.__class__.__name__, "CodexAgentProvider")

    def test_format_provider_model_for_codex(self) -> None:
        with patch.dict(
            os.environ,
            _env(
                AGENT_PROVIDER="codex",
                CODEX_API_KEY="sk-test",
                CODEX_MODEL="gpt-5.4-mini",
                CODEX_REASONING_EFFORT="low",
            ),
            clear=True,
        ):
            settings = Settings(_env_file=None)
            formatted = format_provider_model(settings)
        self.assertIn("provider=codex", formatted)
        self.assertIn("effort=low", formatted)


class CodexExecCommandTests(unittest.TestCase):
    """Validate codex exec CLI arguments for current Codex versions."""

    def test_build_exec_command_uses_current_cli_flags(self) -> None:
        with patch.dict(
            os.environ,
            _env(AGENT_PROVIDER="codex", CODEX_API_KEY="sk-test"),
            clear=True,
        ):
            settings = Settings(_env_file=None)
            provider = CodexAgentProvider(settings)
            command = provider._build_exec_command()

        self.assertNotIn("-a", command)
        self.assertIn("-m", command)
        self.assertIn("-C", command)
        self.assertIn("-s", command)
        self.assertEqual(command[-1], "-")


if __name__ == "__main__":
    unittest.main()
