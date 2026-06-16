import logging
from dataclasses import dataclass
from pathlib import Path

from cursor_sdk import Agent, AgentOptions, CursorAgentError, HttpMcpServerConfig, LocalAgentOptions

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class TaggingResult:
    document_id: int
    status: str
    run_id: str | None = None
    summary: str | None = None
    error: str | None = None


class DocumentTagger:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.template_path = Path(settings.prompt_template_path)

    def _load_template(self) -> str:
        if not self.template_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {self.template_path}")
        return self.template_path.read_text(encoding="utf-8")

    def _render_prompt(
        self,
        document_id: int,
        doc_title: str | None,
        correspondent: str | None,
        document_type: str | None,
        doc_url: str | None,
    ) -> str:
        template = self._load_template()
        replacements = {
            "{{document_id}}": str(document_id),
            "{{doc_title}}": doc_title or "unbekannt",
            "{{correspondent}}": correspondent or "unbekannt",
            "{{document_type}}": document_type or "unbekannt",
            "{{doc_url}}": doc_url or "unbekannt",
        }
        prompt = template
        for key, value in replacements.items():
            prompt = prompt.replace(key, value)
        return prompt

    def tag_document(
        self,
        document_id: int,
        doc_title: str | None = None,
        correspondent: str | None = None,
        document_type: str | None = None,
        doc_url: str | None = None,
    ) -> TaggingResult:
        prompt = self._render_prompt(
            document_id=document_id,
            doc_title=doc_title,
            correspondent=correspondent,
            document_type=document_type,
            doc_url=doc_url,
        )

        logger.info("Starting Cursor agent for document %s", document_id)

        try:
            result = Agent.prompt(
                prompt,
                AgentOptions(
                    api_key=self.settings.cursor_api_key,
                    model=self.settings.cursor_model,
                    local=LocalAgentOptions(
                        cwd=self.settings.agent_cwd,
                        setting_sources=[],
                    ),
                    mcp_servers={
                        "paperless": HttpMcpServerConfig(
                            url=self.settings.paperless_mcp_url,
                        ),
                    },
                ),
            )
        except CursorAgentError as exc:
            logger.exception("Cursor agent failed to start for document %s", document_id)
            return TaggingResult(
                document_id=document_id,
                status="startup_error",
                error=str(exc),
            )

        if result.status == "error":
            logger.error(
                "Cursor agent run failed for document %s (run_id=%s)",
                document_id,
                result.id,
            )
            return TaggingResult(
                document_id=document_id,
                status="run_error",
                run_id=result.id,
                error=getattr(result, "result", None) or "Agent run failed",
            )

        summary = getattr(result, "result", None)
        logger.info(
            "Cursor agent finished for document %s (run_id=%s)",
            document_id,
            result.id,
        )
        return TaggingResult(
            document_id=document_id,
            status="finished",
            run_id=result.id,
            summary=summary,
        )


def exit_code_for_result(result: TaggingResult) -> int:
    """Map tagging outcomes to process exit codes for CLI wrappers."""
    if result.status == "finished":
        return 0
    if result.status == "startup_error":
        return 1
    if result.status == "run_error":
        return 2
    return 3
