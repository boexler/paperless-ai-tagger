import logging
from dataclasses import dataclass
from pathlib import Path

from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions, StdioMcpServerConfig

from app.config import Settings

logger = logging.getLogger(__name__)

LOG_TRUNCATE_LENGTH = 500


class _AgentStreamLogBuffer:
    """Accumulates token-level agent stream chunks into readable log lines."""

    def __init__(self, document_id: int, max_line_length: int = LOG_TRUNCATE_LENGTH) -> None:
        self.document_id = document_id
        self.max_line_length = max_line_length
        self._buffers: dict[str, str] = {"assistant": "", "thinking": ""}
        self._last_msg_type: str | None = None

    def append(self, msg_type: str, text: str) -> None:
        """Append a stream chunk, flushing on message-type changes."""
        if msg_type not in self._buffers or not text:
            return
        if self._last_msg_type and self._last_msg_type != msg_type:
            self.flush(self._last_msg_type)
        self._last_msg_type = msg_type
        self._append_to_buffer(msg_type, text)

    def _append_to_buffer(self, kind: str, text: str) -> None:
        """Append text and emit 500-char blocks when the buffer exceeds the limit."""
        buffer = self._buffers[kind] + text
        while len(buffer) >= self.max_line_length:
            self._emit(kind, buffer[: self.max_line_length])
            buffer = buffer[self.max_line_length :]
        self._buffers[kind] = buffer

    def flush(self, kind: str | None = None) -> None:
        """Emit buffered text for one kind or for all kinds when kind is None."""
        kinds = [kind] if kind else list(self._buffers.keys())
        for buffer_kind in kinds:
            text = self._buffers[buffer_kind].strip()
            if text:
                self._emit(buffer_kind, text)
            self._buffers[buffer_kind] = ""

    def flush_all(self) -> None:
        """Emit all remaining buffered assistant and thinking text."""
        self.flush(None)

    def _emit(self, kind: str, text: str) -> None:
        """Write one consolidated log line for assistant or thinking output."""
        if kind == "assistant":
            logger.info("Agent assistant (document %s): %s", self.document_id, text)
        elif kind == "thinking":
            logger.info("Agent thinking (document %s): %s", self.document_id, text)


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
        stream_buffer: _AgentStreamLogBuffer,
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
        stream_buffer = _AgentStreamLogBuffer(document_id)

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
