"""Single-shot OpenRouter orchestration: classify + tags + tax → apply."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.paperless_client import PaperlessClient, PaperlessClientError
from app.providers.openrouter.client import OpenRouterClient, OpenRouterClientError
from app.providers.openrouter.schemas import (
    ClassificationResult,
    DocumentTaggingResult,
    TagSelectionResult,
    TaxReviewResult,
)

logger = logging.getLogger(__name__)

OPENROUTER_PROMPTS_DIR = Path("/app/prompts/openrouter")
COMBINED_PROMPT_FILE = "03-tag-document-tax.md"

REQUIRED_PROCESS_TAGS = ("ai-tag-document", "ai-tag-tax")
# Process/review/tax markers may always be created; taxonomy new tags are capped.
EXEMPT_FROM_NEW_TAG_LIMIT = frozenset(
    name.casefold()
    for name in (
        *REQUIRED_PROCESS_TAGS,
        "ai-review-tag-document",
        "ai-review-tag-tax",
        "steuerrelevant",
    )
)
MAX_NEW_TAGS = 2
# Paperless created field expects an ISO calendar date (YYYY-MM-DD).
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class OpenRouterOrchestratorError(Exception):
    """Raised when the OpenRouter tagging pipeline fails."""


class OpenRouterOrchestrator:
    """Runs one LLM call then applies results via Paperless REST."""

    def __init__(
        self,
        settings: Settings,
        paperless: PaperlessClient | None = None,
        llm: OpenRouterClient | None = None,
        prompts_dir: Path | None = None,
    ) -> None:
        self.settings = settings
        self.paperless = paperless or PaperlessClient(
            settings.paperless_url,
            settings.paperless_api_token,
        )
        self.llm = llm or OpenRouterClient(settings)
        self.prompts_dir = prompts_dir or _resolve_prompts_dir()
        self._owns_paperless = paperless is None

    def close(self) -> None:
        """Close owned Paperless client resources."""
        if self._owns_paperless:
            self.paperless.close()

    def run(self, document_id: int) -> str:
        """Execute load → single LLM call → apply and return a short summary."""
        logger.info("OpenRouter load context for document %s", document_id)
        context = self._load_context(document_id)

        logger.info("OpenRouter single-shot tagging for document %s", document_id)
        result = self._run_tagging(context)

        logger.info("OpenRouter apply for document %s", document_id)
        return self._apply(
            document_id,
            context,
            result.classification,
            result.tags,
            result.tax,
        )

    def _load_prompt(self, filename: str) -> str:
        path = self.prompts_dir / filename
        if not path.exists():
            raise OpenRouterOrchestratorError(f"OpenRouter prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    def _load_context(self, document_id: int) -> dict[str, Any]:
        try:
            document = self.paperless.get_document(document_id)
            tags = self.paperless.list_tags()
            correspondents = self.paperless.list_correspondents()
            document_types = self.paperless.list_document_types()
        except PaperlessClientError as exc:
            raise OpenRouterOrchestratorError(str(exc)) from exc

        content = str(document.get("content") or "")
        max_chars = self.settings.openrouter_max_content_chars
        truncated = False
        if len(content) > max_chars:
            content = content[:max_chars]
            truncated = True

        existing_tag_ids = _as_int_list(document.get("tags"))
        tags_by_id = {int(t["id"]): str(t.get("name") or "") for t in tags if "id" in t}
        tags_by_name = {name.casefold(): tag_id for tag_id, name in tags_by_id.items() if name}

        return {
            "document": document,
            "content": content,
            "content_truncated": truncated,
            "tags": tags,
            "correspondents": correspondents,
            "document_types": document_types,
            "existing_tag_ids": existing_tag_ids,
            "tags_by_id": tags_by_id,
            "tags_by_name": tags_by_name,
            "correspondents_by_id": {
                int(c["id"]): c for c in correspondents if "id" in c
            },
            "document_types_by_id": {
                int(d["id"]): d for d in document_types if "id" in d
            },
        }

    def _run_tagging(self, context: dict[str, Any]) -> DocumentTaggingResult:
        system = self._load_prompt(COMBINED_PROMPT_FILE)
        user = _build_tagging_user_prompt(context)
        try:
            return self.llm.complete_json(system, user, DocumentTaggingResult)
        except OpenRouterClientError as exc:
            raise OpenRouterOrchestratorError(f"Tagging request failed: {exc}") from exc

    def _apply(
        self,
        document_id: int,
        context: dict[str, Any],
        classification: ClassificationResult,
        tags: TagSelectionResult,
        tax: TaxReviewResult,
    ) -> str:
        tags_by_name: dict[str, int] = dict(context["tags_by_name"])
        update_fields: dict[str, Any] = {}
        note_lines: list[str] = ["Automatische Einordnung:"]

        try:
            correspondent_id, corr_note = self._resolve_correspondent(
                classification,
                context,
            )
            if correspondent_id is not None:
                update_fields["correspondent"] = correspondent_id
            elif classification.correspondent.action == "clear":
                update_fields["correspondent"] = None
            note_lines.append(f"- {corr_note}")

            document_type_id, type_note = self._resolve_document_type(
                classification,
                context,
            )
            if document_type_id is not None:
                update_fields["document_type"] = document_type_id
            elif classification.document_type.action == "clear":
                update_fields["document_type"] = None
            note_lines.append(f"- {type_note}")

            if classification.title.action == "set" and classification.title.value:
                update_fields["title"] = classification.title.value.strip()
                note_lines.append(
                    f'- Titel geändert zu "{classification.title.value.strip()}".',
                )
            else:
                note_lines.append("- Titel unverändert.")

            created_note = self._apply_created_date(classification, update_fields)
            note_lines.append(f"- {created_note}")

            if classification.classification_note:
                note_lines.append(f"- {classification.classification_note}")

            merged_tag_ids, tag_notes, created_names = self._resolve_tags(
                context,
                tags,
                tax,
                classification,
                tags_by_name,
            )
            update_fields["tags"] = merged_tag_ids
            note_lines.extend(tag_notes)

            note_lines.append("")
            note_lines.append("Steuerprüfung:")
            note_lines.append(f"- Ergebnis: {_tax_result_label(tax.result)}.")
            if tax.tax_note:
                note_lines.append(f"- {tax.tax_note}")
            note_lines.append(f"- Beruflicher Kontext: {tax.professional_context}.")
            note_lines.append("- ai-tag-tax wurde gesetzt.")
            if tax.needs_review or "ai-review-tag-tax" in {
                n.casefold() for n in [*tax.tags_to_add, *tax.new_tags]
            }:
                note_lines.append("- ai-review-tag-tax wurde gesetzt.")
            else:
                note_lines.append("- ai-review-tag-tax wurde nicht gesetzt.")

            self.paperless.update_document(document_id, **update_fields)
            note_text = "\n".join(note_lines)
            self.paperless.add_document_note(document_id, note_text)
        except (PaperlessClientError, OpenRouterOrchestratorError) as exc:
            raise OpenRouterOrchestratorError(str(exc)) from exc

        title = update_fields.get("title") or context["document"].get("title") or ""
        summary = (
            f"Dokument {document_id}: Titel={title!r}; "
            f"Tags={len(merged_tag_ids)}; Steuer={tax.result}; "
            f"neu={', '.join(created_names) or 'keine'}."
        )
        return summary

    def _apply_created_date(
        self,
        classification: ClassificationResult,
        update_fields: dict[str, Any],
    ) -> str:
        """Apply a validated ISO created date from the LLM, or keep the current value."""
        decision = classification.created
        if decision.action != "set" or not decision.value:
            return "Datum unverändert."

        value = decision.value.strip()
        if not _ISO_DATE_RE.fullmatch(value):
            logger.warning(
                "Ignoring invalid created date from LLM: %r (reason=%r)",
                decision.value,
                decision.reason,
            )
            return "Datum unverändert (ungültiges Format vom Modell)."

        update_fields["created"] = value
        return f'Datum geändert zu "{value}".'

    def _resolve_correspondent(
        self,
        classification: ClassificationResult,
        context: dict[str, Any],
    ) -> tuple[int | None, str]:
        decision = classification.correspondent
        current = context["document"].get("correspondent")

        if decision.action == "keep":
            return (
                int(current) if current is not None else None,
                "Korrespondent unverändert.",
            )
        if decision.action == "clear":
            return None, "Korrespondent entfernt."
        if decision.action == "set_existing":
            if decision.id is None:
                raise OpenRouterOrchestratorError(
                    "correspondent.set_existing requires id",
                )
            corr = context["correspondents_by_id"].get(decision.id)
            if corr is None:
                raise OpenRouterOrchestratorError(
                    f"Unknown correspondent id={decision.id}",
                )
            if decision.update_match and decision.match:
                self.paperless.update_correspondent(
                    decision.id,
                    match=decision.match,
                    matching_algorithm=decision.matching_algorithm or 4,
                    is_insensitive=True,
                )
                return decision.id, (
                    f"Korrespondent gesetzt: {corr.get('name')} "
                    f"(Regex nachgepflegt)."
                )
            return decision.id, f"Korrespondent gesetzt: {corr.get('name')}."
        if decision.action == "create":
            if not decision.name or not decision.match:
                raise OpenRouterOrchestratorError(
                    "correspondent.create requires name and match",
                )
            created = self.paperless.create_correspondent(
                name=decision.name,
                match=decision.match,
                matching_algorithm=decision.matching_algorithm or 4,
            )
            return int(created["id"]), f"Korrespondent angelegt: {decision.name}."
        return (
            int(current) if current is not None else None,
            "Korrespondent unverändert.",
        )

    def _resolve_document_type(
        self,
        classification: ClassificationResult,
        context: dict[str, Any],
    ) -> tuple[int | None, str]:
        decision = classification.document_type
        current = context["document"].get("document_type")

        if decision.action == "keep":
            return (
                int(current) if current is not None else None,
                "Dokumenttyp unverändert.",
            )
        if decision.action == "clear":
            return None, "Dokumenttyp entfernt."
        if decision.action == "set_existing":
            if decision.id is None:
                raise OpenRouterOrchestratorError(
                    "document_type.set_existing requires id",
                )
            doc_type = context["document_types_by_id"].get(decision.id)
            if doc_type is None:
                raise OpenRouterOrchestratorError(
                    f"Unknown document_type id={decision.id}",
                )
            return decision.id, f"Dokumenttyp gesetzt: {doc_type.get('name')}."
        if decision.action == "create":
            if not decision.name:
                raise OpenRouterOrchestratorError("document_type.create requires name")
            created = self.paperless.create_document_type(decision.name)
            return int(created["id"]), f"Dokumenttyp angelegt: {decision.name}."
        return (
            int(current) if current is not None else None,
            "Dokumenttyp unverändert.",
        )

    def _resolve_tags(
        self,
        context: dict[str, Any],
        tags: TagSelectionResult,
        tax: TaxReviewResult,
        classification: ClassificationResult,
        tags_by_name: dict[str, int],
    ) -> tuple[list[int], list[str], list[str]]:
        """Merge existing tags with LLM selections; never drop existing IDs."""
        merged: set[int] = set(context["existing_tag_ids"])
        notes: list[str] = []
        created: list[str] = []
        tags_by_id: dict[int, str] = dict(context["tags_by_id"])

        names_to_ensure: list[str] = []
        for name in [*tags.tags_to_add, *tags.new_tags, *tax.tags_to_add, *tax.new_tags]:
            cleaned = name.strip()
            if cleaned:
                names_to_ensure.append(cleaned)

        for required in REQUIRED_PROCESS_TAGS:
            if required.casefold() not in {n.casefold() for n in names_to_ensure}:
                names_to_ensure.append(required)

        if tags.needs_review or classification.needs_review:
            if "ai-review-tag-document".casefold() not in {
                n.casefold() for n in names_to_ensure
            }:
                names_to_ensure.append("ai-review-tag-document")

        if tax.needs_review or tax.result == "maybe":
            if "ai-review-tag-tax".casefold() not in {
                n.casefold() for n in names_to_ensure
            }:
                names_to_ensure.append("ai-review-tag-tax")

        if tax.result == "relevant":
            if "steuerrelevant".casefold() not in {n.casefold() for n in names_to_ensure}:
                names_to_ensure.append("steuerrelevant")

        unique_names: list[str] = []
        seen: set[str] = set()
        for name in names_to_ensure:
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique_names.append(name)

        new_count = 0
        for name in unique_names:
            existing_id = tags_by_name.get(name.casefold())
            if existing_id is not None:
                merged.add(existing_id)
                continue
            counts_toward_limit = name.casefold() not in EXEMPT_FROM_NEW_TAG_LIMIT
            if counts_toward_limit and new_count >= MAX_NEW_TAGS:
                notes.append(
                    f'- Neues Tag "{name}" übersprungen (Limit {MAX_NEW_TAGS}).',
                )
                continue
            tag_id = self.paperless.ensure_tag(name, tags_by_name)
            merged.add(tag_id)
            tags_by_id[tag_id] = name
            created.append(name)
            if counts_toward_limit:
                new_count += 1

        for name, tag_id in tags_by_name.items():
            tags_by_id.setdefault(tag_id, name)
        added_names = [
            tags_by_id.get(tag_id, str(tag_id))
            for tag_id in sorted(merged)
            if tag_id not in context["existing_tag_ids"]
        ]
        notes.append(
            f"- Tags ergänzt: {', '.join(added_names) or 'keine'}."
            if added_names
            else "- Keine zusätzlichen Tags ergänzt.",
        )
        if tags.tags_note:
            notes.append(f"- {tags.tags_note}")
        notes.append("- ai-tag-document wurde gesetzt.")
        if tags.needs_review or classification.needs_review:
            notes.append("- ai-review-tag-document wurde gesetzt.")
        else:
            notes.append("- ai-review-tag-document wurde nicht gesetzt.")
        if created:
            notes.append(f"- Neue Tags angelegt: {', '.join(created)}.")
        else:
            notes.append("- Keine neuen Tags angelegt.")
        if tags.suggested_tags:
            notes.append(
                f'- Vorschläge (nicht angelegt): {", ".join(tags.suggested_tags)}.',
            )

        return sorted(merged), notes, created


def _tax_result_label(result: str) -> str:
    return {
        "relevant": "steuerlich relevant",
        "maybe": "möglicherweise steuerlich relevant",
        "none": "kein klarer Steuerbezug erkannt",
    }.get(result, result)


def _as_int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


def _compact_catalog(items: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in items:
        compact.append({field: item.get(field) for field in fields})
    return compact


def _build_tagging_user_prompt(context: dict[str, Any]) -> str:
    document = context["document"]
    payload = {
        "document": {
            "id": document.get("id"),
            "title": document.get("title"),
            "correspondent": document.get("correspondent"),
            "document_type": document.get("document_type"),
            "existing_tags": [
                {"id": tag_id, "name": context["tags_by_id"].get(tag_id, str(tag_id))}
                for tag_id in context["existing_tag_ids"]
            ],
            "created": document.get("created"),
            "content_truncated": context["content_truncated"],
            "content": context["content"],
        },
        "correspondents": _compact_catalog(
            context["correspondents"],
            ("id", "name", "match", "matching_algorithm", "is_insensitive"),
        ),
        "document_types": _compact_catalog(
            context["document_types"],
            ("id", "name"),
        ),
        "available_tags": _compact_catalog(context["tags"], ("id", "name")),
    }
    return (
        "Klassifiziere, tagge und prüfe die Steuerrelevanz. Antworte nur mit JSON.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _local_prompts_fallback() -> Path | None:
    """Find prompts/openrouter by walking up from this file (local dev checkout)."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "prompts" / "openrouter"
        if candidate.is_dir():
            return candidate
    return None


def _resolve_prompts_dir() -> Path:
    """Prefer Docker path, then a repo-relative prompts/openrouter directory."""
    if OPENROUTER_PROMPTS_DIR.is_dir():
        return OPENROUTER_PROMPTS_DIR
    local = _local_prompts_fallback()
    if local is not None:
        return local
    return OPENROUTER_PROMPTS_DIR
