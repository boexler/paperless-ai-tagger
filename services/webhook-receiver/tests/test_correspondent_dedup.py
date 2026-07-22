"""Unit tests for correspondent name deduplication."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.config import Settings
from app.correspondent_dedup import (
    correspondent_name_tokens,
    correspondent_similarity_score,
    find_duplicate_correspondent,
    merge_correspondent_match,
)
from app.providers.openrouter.orchestrator import OpenRouterOrchestrator
from app.providers.openrouter.schemas import (
    ClassificationResult,
    CorrespondentDecision,
    DocumentTaggingResult,
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


class CorrespondentDedupHelperTests(unittest.TestCase):
    """Validate normalization and similarity scoring."""

    def test_expands_stb_abbreviation(self) -> None:
        tokens = correspondent_name_tokens("Grünewald StB")
        self.assertEqual(tokens, frozenset({"gruenewald", "steuerberater"}))

    def test_gruenewald_variants_are_duplicates(self) -> None:
        score = correspondent_similarity_score(
            "Grünewald StB",
            "Lothar Grünewald Steuerberater",
        )
        self.assertEqual(score, 1.0)
        duplicate = find_duplicate_correspondent(
            "Grünewald StB",
            [
                {
                    "id": 131,
                    "name": "Lothar Grünewald Steuerberater",
                    "match": r".*gruenewald-steuerberatung\.de.*",
                },
            ],
        )
        self.assertIsNotNone(duplicate)
        assert duplicate is not None
        self.assertEqual(duplicate["id"], 131)

    def test_unrelated_names_do_not_match(self) -> None:
        score = correspondent_similarity_score("Contabo GmbH", "PayPal")
        self.assertEqual(score, 0.0)
        self.assertIsNone(
            find_duplicate_correspondent(
                "Contabo GmbH",
                [{"id": 29, "name": "PayPal", "match": "PayPal"}],
            ),
        )

    def test_ambiguous_best_score_returns_none(self) -> None:
        duplicate = find_duplicate_correspondent(
            "Muster",
            [
                {"id": 1, "name": "Muster GmbH"},
                {"id": 2, "name": "Muster AG"},
            ],
        )
        self.assertIsNone(duplicate)

    def test_weak_shared_prefix_does_not_merge(self) -> None:
        self.assertIsNone(
            find_duplicate_correspondent(
                "Bayern Service",
                [
                    {"id": 1, "name": "Bayernwerk Netz GmbH"},
                    {"id": 2, "name": "Bayern-Versicherung Lebensversicherung AG"},
                ],
            ),
        )

    def test_merge_correspondent_match_alternation(self) -> None:
        merged = merge_correspondent_match(
            r".*gruenewald-steuerberatung\.de.*",
            r"Grünewald\s+StB",
        )
        self.assertIn("gruenewald-steuerberatung", merged or "")
        self.assertIn("Grünewald", merged or "")
        self.assertIn("|", merged or "")


class CorrespondentCreateDedupOrchestratorTests(unittest.TestCase):
    """Validate create→existing redirect in the OpenRouter apply path."""

    def setUp(self) -> None:
        self.prompts_dir = Path(tempfile.mkdtemp())
        (self.prompts_dir / "03-tag-document-tax.md").write_text(
            "tag document",
            encoding="utf-8",
        )
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

    def test_create_redirects_to_similar_existing_correspondent(self) -> None:
        """LLM create for Grünewald StB must reuse Lothar Grünewald Steuerberater."""
        self.paperless.get_document.return_value = {
            "id": 50,
            "title": "Schreiben",
            "correspondent": None,
            "document_type": None,
            "tags": [],
            "content": "Dipl.-Kfrn. Lothar Grünewald StB",
        }
        self.paperless.list_tags.return_value = [
            {"id": 20, "name": "ai-tag-document"},
            {"id": 21, "name": "ai-tag-tax"},
        ]
        self.paperless.list_correspondents.return_value = [
            {
                "id": 131,
                "name": "Lothar Grünewald Steuerberater",
                "match": r".*gruenewald-steuerberatung\.de.*",
                "matching_algorithm": 4,
            },
        ]
        self.paperless.list_document_types.return_value = []
        self.paperless.ensure_tag.side_effect = lambda name, tags_by_name: {
            "ai-tag-document": 20,
            "ai-tag-tax": 21,
        }[name]
        self.llm.complete_json.return_value = DocumentTaggingResult(
            classification=ClassificationResult(
                correspondent=CorrespondentDecision(
                    action="create",
                    name="Grünewald StB",
                    match=r"Grünewald\s+StB|Dipl\.-Kfrn\.\s*Lothar\s+Grünewald",
                    matching_algorithm=4,
                ),
                document_type=DocumentTypeDecision(action="keep"),
                title=TitleDecision(action="keep"),
            ),
            tags=TagSelectionResult(tags_to_add=["ai-tag-document"]),
            tax=TaxReviewResult(result="none", tags_to_add=["ai-tag-tax"]),
        )

        self.orchestrator.run(50)

        self.paperless.create_correspondent.assert_not_called()
        self.paperless.update_correspondent.assert_called_once()
        update_kwargs = self.paperless.update_correspondent.call_args
        self.assertEqual(update_kwargs.args[0], 131)
        self.assertIn("match", update_kwargs.kwargs)
        doc_kwargs = self.paperless.update_document.call_args.kwargs
        self.assertEqual(doc_kwargs["correspondent"], 131)
        note = self.paperless.add_document_note.call_args.args[1]
        self.assertIn("Lothar Grünewald Steuerberater", note)
        self.assertIn("statt neuem", note)


if __name__ == "__main__":
    unittest.main()
