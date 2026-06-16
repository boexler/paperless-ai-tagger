import logging
from dataclasses import dataclass
from pathlib import Path

from cursor_sdk import Agent, AgentOptions, CursorAgentError, HttpMcpServerConfig, LocalAgentOptions

from app.config import Settings

logger = logging.getLogger(__name__)

LOG_TRUNCATE_LENGTH = 500


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

    def _build_agent_options(self) -> AgentOptions:
        return AgentOptions(
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
        )

    def _truncate_for_log(self, value: object) -> str:
        text = str(value)
        if len(text) <= LOG_TRUNCATE_LENGTH:
            return text
        return f"{text[:LOG_TRUNCATE_LENGTH]}..."

    def _log_agent_message(self, document_id: int, message: object) -> str | None:
        """Log agent stream messages and return a tool error summary when present."""
        msg_type = getattr(message, "type", None)

        if msg_type == "assistant":
            content = getattr(getattr(message, "message", None), "content", None) or []
            for block in content:
                if getattr(block, "type", None) == "text":
                    text = getattr(block, "text", "").strip()
                    if text:
                        logger.info("Agent assistant (document %s): %s", document_id, text)
            return None

        if msg_type == "thinking":
            text = getattr(message, "text", "").strip()
            if text:
                logger.info(
                    "Agent thinking (document %s): %s",
                    document_id,
                    self._truncate_for_log(text),
                )
            return None

        if msg_type == "tool_call":
            name = getattr(message, "name", "?")
            status = getattr(message, "status", "?")
            args = self._truncate_for_log(getattr(message, "args", ""))
            result = self._truncate_for_log(getattr(message, "result", ""))
            logger.info(
                "Agent tool %s (document %s) status=%s args=%s result=%s",
                name,
                document_id,
                status,
                args,
                result,
            )
            if status == "error":
                return f"{name}: {result or 'tool call failed'}"
            return None

        if msg_type == "status":
            status_text = getattr(message, "message", None) or getattr(message, "status", "")
            if status_text:
                logger.info("Agent status (document %s): %s", document_id, status_text)
            return None

        return None

    def _run_agent_with_logging(self, document_id: int, prompt: str):
        """Run the Cursor agent and log assistant output, thinking, and tool calls."""
        tool_errors: list[str] = []

        with Agent.create(self._build_agent_options()) as agent:
            run = agent.send(prompt)
            for message in run.messages():
                tool_error = self._log_agent_message(document_id, message)
                if tool_error:
                    tool_errors.append(tool_error)
            result = run.wait()

        return result, tool_errors

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
            result, tool_errors = self._run_agent_with_logging(document_id, prompt)
        except CursorAgentError as exc:
            logger.exception("Cursor agent failed to start for document %s", document_id)
            return TaggingResult(
                document_id=document_id,
                status="startup_error",
                error=str(exc),
            )

        if result.status == "error":
            error_message = getattr(result, "result", None) or ""
            if not str(error_message).strip() and tool_errors:
                error_message = "; ".join(tool_errors)
            if not str(error_message).strip():
                error_message = "Agent run failed"
            logger.error(
                "Cursor agent run failed for document %s (run_id=%s): %s",
                document_id,
                result.id,
                error_message,
            )
            return TaggingResult(
                document_id=document_id,
                status="run_error",
                run_id=result.id,
                error=str(error_message),
            )

        summary = getattr(result, "result", None)
        if summary:
            logger.info(
                "Agent summary (document %s): %s",
                document_id,
                self._truncate_for_log(summary),
            )
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
