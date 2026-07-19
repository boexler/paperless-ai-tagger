import logging

from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions, StdioMcpServerConfig

from app.config import Settings
from app.model_params import build_cursor_model_selection
from app.providers.base import TaggingResult
from app.providers.prompt import render_prompt
from app.providers.stream_log import AgentStreamLogBuffer

logger = logging.getLogger(__name__)

LOG_TRUNCATE_LENGTH = 500


class CursorAgentProvider:
    """Tags documents via the Cursor Python SDK."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _build_agent_options(self) -> AgentOptions:
        return AgentOptions(
            api_key=self.settings.cursor_api_key or "",
            model=build_cursor_model_selection(
                self.settings.cursor_model,
                self.settings.cursor_model_params,
            ),
            local=LocalAgentOptions(
                cwd=self.settings.agent_cwd,
                setting_sources=[],
            ),
            mcp_servers={
                "paperless": StdioMcpServerConfig(
                    command=self.settings.paperless_mcp_command,
                    args=["mcp"],
                    env={
                        "PAPERLESS_URL": self.settings.paperless_url,
                        "PAPERLESS_TOKEN": self.settings.paperless_api_token,
                    },
                ),
            },
        )

    def _truncate_for_log(self, value: object) -> str:
        text = str(value)
        if len(text) <= LOG_TRUNCATE_LENGTH:
            return text
        return f"{text[:LOG_TRUNCATE_LENGTH]}..."

    def _log_agent_message(
        self,
        document_id: int,
        message: object,
        stream_buffer: AgentStreamLogBuffer,
    ) -> str | None:
        """Log agent stream messages and return a tool error summary when present."""
        msg_type = getattr(message, "type", None)

        if msg_type == "assistant":
            content = getattr(getattr(message, "message", None), "content", None) or []
            for block in content:
                if getattr(block, "type", None) == "text":
                    stream_buffer.append("assistant", getattr(block, "text", ""))
            return None

        if msg_type == "thinking":
            stream_buffer.append("thinking", getattr(message, "text", ""))
            return None

        if msg_type == "tool_call":
            stream_buffer.flush_all()
            name = getattr(message, "name", "?")
            status = getattr(message, "status", "?")
            if status not in ("completed", "error"):
                return None
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
            stream_buffer.flush_all()
            status_text = getattr(message, "message", None) or getattr(message, "status", "")
            if status_text:
                logger.info("Agent status (document %s): %s", document_id, status_text)
            return None

        return None

    def _run_agent_with_logging(self, document_id: int, prompt: str):
        """Run the Cursor agent and log assistant output, thinking, and tool calls."""
        tool_errors: list[str] = []
        stream_buffer = AgentStreamLogBuffer(document_id)

        with Agent.create(self._build_agent_options()) as agent:
            run = agent.send(prompt)
            try:
                for message in run.messages():
                    tool_error = self._log_agent_message(document_id, message, stream_buffer)
                    if tool_error:
                        tool_errors.append(tool_error)
            finally:
                stream_buffer.flush_all()
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
        prompt = render_prompt(
            self.settings,
            document_id,
            doc_title,
            correspondent,
            document_type,
            doc_url,
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
