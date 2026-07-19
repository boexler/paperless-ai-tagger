import logging

logger = logging.getLogger(__name__)

LOG_TRUNCATE_LENGTH = 500


class AgentStreamLogBuffer:
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
