"""OpenRouter single-shot tagging provider (no MCP tool calling)."""

from __future__ import annotations

import logging
import uuid

from app.config import Settings
from app.paperless_client import PaperlessClientError
from app.providers.base import TaggingResult
from app.providers.openrouter.orchestrator import (
    OpenRouterOrchestrator,
    OpenRouterOrchestratorError,
)

logger = logging.getLogger(__name__)


class OpenRouterAgentProvider:
    """Tags documents via one OpenRouter JSON call + Paperless REST apply."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def tag_document(
        self,
        document_id: int,
        doc_title: str | None = None,
        correspondent: str | None = None,
        document_type: str | None = None,
        doc_url: str | None = None,
    ) -> TaggingResult:
        """Run the OpenRouter single-shot tagging → apply pipeline."""
        _ = (doc_title, correspondent, document_type, doc_url)
        run_id = str(uuid.uuid4())
        logger.info(
            "Starting OpenRouter agent for document %s (model=%s)",
            document_id,
            self.settings.openrouter_model,
        )

        orchestrator = OpenRouterOrchestrator(self.settings)
        try:
            summary = orchestrator.run(document_id)
        except OpenRouterOrchestratorError as exc:
            logger.error(
                "OpenRouter agent failed for document %s (run_id=%s): %s",
                document_id,
                run_id,
                exc,
            )
            self._mark_failure(orchestrator, document_id, str(exc))
            return TaggingResult(
                document_id=document_id,
                status="run_error",
                run_id=run_id,
                error=str(exc),
            )
        except Exception as exc:
            logger.exception(
                "OpenRouter agent startup/runtime error for document %s",
                document_id,
            )
            self._mark_failure(orchestrator, document_id, str(exc))
            return TaggingResult(
                document_id=document_id,
                status="startup_error",
                run_id=run_id,
                error=str(exc),
            )
        finally:
            orchestrator.close()

        logger.info(
            "OpenRouter agent finished for document %s (run_id=%s): %s",
            document_id,
            run_id,
            summary,
        )
        return TaggingResult(
            document_id=document_id,
            status="finished",
            run_id=run_id,
            summary=summary,
        )

    def _mark_failure(
        self,
        orchestrator: OpenRouterOrchestrator,
        document_id: int,
        error: str,
    ) -> None:
        """Best-effort Paperless ai-error tag + note; never mask the original error."""
        try:
            orchestrator.mark_processing_failure(document_id, error)
        except PaperlessClientError as mark_exc:
            logger.error(
                "Could not mark document %s after OpenRouter failure: %s",
                document_id,
                mark_exc,
            )
        except Exception:
            logger.exception(
                "Unexpected error while marking document %s after OpenRouter failure",
                document_id,
            )
