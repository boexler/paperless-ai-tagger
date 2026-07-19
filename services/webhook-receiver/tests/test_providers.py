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


class CodexOutputParsingTests(unittest.TestCase):
    """Validate Codex JSON event parsing and logging."""

    def _provider(self) -> CodexAgentProvider:
        with patch.dict(
            os.environ,
            _env(AGENT_PROVIDER="codex", CODEX_API_KEY="sk-test"),
            clear=True,
        ):
            settings = Settings(_env_file=None)
            return CodexAgentProvider(settings)

    def test_parse_current_mcp_tool_call_event(self) -> None:
        provider = self._provider()
        stdout = "\n".join(
            [
                '{"type":"turn.started"}',
                (
                    '{"type":"item.completed","item":{"type":"mcp_tool_call",'
                    '"server":"paperless","name":"update_document","status":"completed",'
                    '"arguments":{"document_id":1028},"output":"updated"}}'
                ),
                (
                    '{"type":"item.completed","item":{"type":"assistant_message",'
                    '"content":[{"type":"text","text":"Document 1028 updated."}]}}'
                ),
            ],
        )

        with self.assertLogs("app.providers.codex", level="INFO") as logs:
            summary, error, tool_errors, event_count, tool_count = provider._parse_codex_output(
                1028,
                stdout,
                "",
            )

        self.assertEqual(summary, "Document 1028 updated.")
        self.assertIsNone(error)
        self.assertEqual(tool_errors, [])
        self.assertEqual(event_count, 3)
        self.assertEqual(tool_count, 1)
        self.assertIn("Agent tool paperless.update_document", "\n".join(logs.output))

    def test_parse_current_mcp_tool_call_error(self) -> None:
        provider = self._provider()
        stdout = (
            '{"type":"item.completed","item":{"type":"mcp_tool_call",'
            '"server":"paperless","name":"update_document","status":"error",'
            '"output":"permission denied"}}'
        )

        summary, error, tool_errors, event_count, tool_count = provider._parse_codex_output(
            1028,
            stdout,
            "",
        )

        self.assertIsNone(summary)
        self.assertEqual(error, "paperless.update_document: permission denied")
        self.assertEqual(tool_errors, ["paperless.update_document: permission denied"])
        self.assertEqual(event_count, 1)
        self.assertEqual(tool_count, 1)


if __name__ == "__main__":
    unittest.main()
