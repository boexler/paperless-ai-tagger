"""Unit tests for OpenRouter settings, factory, and orchestrator apply logic."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from app.config import Settings
from app.providers.factory import create_provider, format_provider_model
from app.providers.openrouter.client import OpenRouterClientError, _extract_json_object
from app.providers.openrouter.orchestrator import OpenRouterOrchestrator
from app.providers.openrouter.schemas import (
    ClassificationResult,
    CorrespondentDecision,
    DocumentTypeDecision,
    TagSelectionResult,
    TaxReviewResult,
    TitleDecision,
)


def _env(**values: str) -> dict[str, str]:
    """Build a minimal environment for Settings initialization."""
    base = {
        "WEBHOOK_SECRET": "secret",
        "PAPERLESS_BASE_URL": "http://paperless:8000",
        "PAPERLESS_API_TOKEN": "token",
    }
    base.update(values)
    return base


class OpenRouterSettingsTests(unittest.TestCase):
    """Validate OpenRouter-specific settings."""

    def test_openrouter_requires_api_key(self) -> None:
        with patch.dict(os.environ, _env(AGENT_PROVIDER="openrouter"), clear=True):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)

    def test_openrouter_accepts_api_key(self) -> None:
        with patch.dict(
            os.environ,
            _env(AGENT_PROVIDER="openrouter", OPENROUTER_API_KEY="sk-or-test"),
            clear=True,
        ):
            settings = Settings(_env_file=None)
            self.assertEqual(settings.agent_provider, "openrouter")
            self.assertEqual(
                settings.openrouter_model,
                "nvidia/nemotron-3-ultra-550b-a55b:free",
            )


class OpenRouterFactoryTests(unittest.TestCase):
    """Validate OpenRouter provider factory wiring."""

    def test_create_openrouter_provider(self) -> None:
        with patch.dict(
            os.environ,
            _env(AGENT_PROVIDER="openrouter", OPENROUTER_API_KEY="sk-or-test"),
            clear=True,
        ):
            settings = Settings(_env_file=None)
            provider = create_provider(settings)
        self.assertEqual(provider.__class__.__name__, "OpenRouterAgentProvider")

    def test_format_provider_model_for_openrouter(self) -> None:
        with patch.dict(
            os.environ,
            _env(
                AGENT_PROVIDER="openrouter",
                OPENROUTER_API_KEY="sk-or-test",
                OPENROUTER_MODEL="openai/gpt-4o-mini",
            ),
            clear=True,
        ):
            settings = Settings(_env_file=None)
            formatted = format_provider_model(settings)
        self.assertIn("provider=openrouter", formatted)
        self.assertIn("openai/gpt-4o-mini", formatted)


class OpenRouterJsonParsingTests(unittest.TestCase):
    """Validate JSON extraction helpers."""

    def test_extract_json_object_from_fence(self) -> None:
        payload = _extract_json_object('```json\n{"result": "none"}\n```')
        self.assertEqual(payload["result"], "none")

    def test_extract_json_object_rejects_invalid(self) -> None:
        with self.assertRaises(OpenRouterClientError):
            _extract_json_object("not json at all")


class OpenRouterClientRetryTests(unittest.TestCase):
    """Validate retries for empty OpenRouter completions."""

    def test_retries_no_choices_then_succeeds(self) -> None:
        from app.providers.openrouter.client import OpenRouterClient
        from app.providers.openrouter.schemas import TaxReviewResult

        with patch.dict(
            os.environ,
            _env(AGENT_PROVIDER="openrouter", OPENROUTER_API_KEY="sk-or-test"),
            clear=True,
        ):
            settings = Settings(_env_file=None)

        client = OpenRouterClient(settings)
        empty = MagicMock()
        empty.choices = []
        ok = MagicMock()
        ok.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"result":"none","tags_to_add":["ai-tag-tax"],'
                    '"new_tags":[],"needs_review":false,'
                    '"professional_context":"keine","tax_note":"ok"}',
                    refusal=None,
                ),
                finish_reason="stop",
            ),
        ]

        with patch.object(
            client._client.chat.completions,
            "create",
            side_effect=[empty, ok],
        ), patch("app.providers.openrouter.client.time.sleep") as sleep_mock:
            with self.assertLogs("app.providers.openrouter.client", level="WARNING") as logs:
                result = client.complete_json("system", "user", TaxReviewResult)

        self.assertEqual(result.result, "none")
        sleep_mock.assert_called_once_with(5.0)
        self.assertTrue(any("no choices" in line for line in logs.output))


class OpenRouterOrchestratorTests(unittest.TestCase):
    """Validate multi-step orchestrator apply behavior with mocks."""

    def setUp(self) -> None:
        self.prompts_dir = Path(tempfile.mkdtemp())
        (self.prompts_dir / "03-classify-metadata.md").write_text("classify", encoding="utf-8")
        (self.prompts_dir / "03-select-tags.md").write_text("tags", encoding="utf-8")
        (self.prompts_dir / "03-tax-review.md").write_text("tax", encoding="utf-8")

        with patch.dict(
            os.environ,
            _env(AGENT_PROVIDER="openrouter", OPENROUTER_API_KEY="sk-or-test"),
            clear=True,
        ):
            self.settings = Settings(_env_file=None)

        self.paperless = MagicMock()
        self.llm = MagicMock()
        self.orchestrator = OpenRouterOrchestrator(
            self.settings,
            paperless=self.paperless,
            llm=self.llm,
            prompts_dir=self.prompts_dir,
        )

    def test_run_success_merges_existing_tags(self) -> None:
        self.paperless.get_document.return_value = {
            "id": 42,
            "title": "Rechnung",
            "correspondent": 7,
            "document_type": 3,
            "tags": [10, 11],
            "content": "Stromrechnung Wohnung",
        }
        self.paperless.list_tags.return_value = [
            {"id": 10, "name": "Finanzen"},
            {"id": 11, "name": "Wohnen"},
            {"id": 20, "name": "ai-tag-document"},
            {"id": 21, "name": "ai-tag-tax"},
            {"id": 22, "name": "Strom"},
        ]
        self.paperless.list_correspondents.return_value = [
            {"id": 7, "name": "Stadtwerke", "match": "Stadtwerke", "matching_algorithm": 4},
        ]
        self.paperless.list_document_types.return_value = [
            {"id": 3, "name": "Rechnung"},
        ]
        self.paperless.ensure_tag.side_effect = lambda name, tags_by_name: {
            "ai-tag-document": 20,
            "ai-tag-tax": 21,
            "Strom": 22,
        }[name]

        self.llm.complete_json.side_effect = [
            ClassificationResult(
                correspondent=CorrespondentDecision(action="keep"),
                document_type=DocumentTypeDecision(action="keep"),
                title=TitleDecision(action="set", value="Rechnung – Stromabschlag"),
                classification_note="Stromrechnung erkannt.",
            ),
            TagSelectionResult(
                tags_to_add=["Strom", "ai-tag-document"],
                new_tags=[],
                tags_note="Allgemeine Tags gesetzt.",
            ),
            TaxReviewResult(
                result="none",
                tags_to_add=["ai-tag-tax"],
                tax_note="Privater Verbrauch.",
            ),
        ]

        summary = self.orchestrator.run(42)

        self.paperless.update_document.assert_called_once()
        kwargs = self.paperless.update_document.call_args.kwargs
        self.assertEqual(kwargs["title"], "Rechnung – Stromabschlag")
        self.assertEqual(sorted(kwargs["tags"]), [10, 11, 20, 21, 22])
        self.paperless.add_document_note.assert_called_once()
        note = self.paperless.add_document_note.call_args.args[1]
        self.assertIn("Automatische Einordnung:", note)
        self.assertIn("Steuerprüfung:", note)
        self.assertIn("Dokument 42", summary)

    def test_run_invalid_json_returns_orchestrator_error(self) -> None:
        self.paperless.get_document.return_value = {
            "id": 1,
            "title": "X",
            "tags": [],
            "content": "text",
        }
        self.paperless.list_tags.return_value = []
        self.paperless.list_correspondents.return_value = []
        self.paperless.list_document_types.return_value = []
        self.llm.complete_json.side_effect = OpenRouterClientError("bad json")

        with self.assertRaises(Exception) as ctx:
            self.orchestrator.run(1)
        self.assertIn("Step 1 classify failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
