import json
import logging
import os
import subprocess
import uuid
from typing import Any

from app.codex_config import write_codex_config
from app.config import Settings
from app.providers.base import TaggingResult
from app.providers.prompt import render_prompt

logger = logging.getLogger(__name__)

LOG_TRUNCATE_LENGTH = 500


class CodexAgentProvider:
    """Tags documents via the OpenAI Codex CLI in non-interactive mode."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._config_path = write_codex_config(settings)
        logger.info("Codex config written to %s", self._config_path)

    def _truncate_for_log(self, value: object) -> str:
        text = str(value)
        if len(text) <= LOG_TRUNCATE_LENGTH:
            return text
        return f"{text[:LOG_TRUNCATE_LENGTH]}..."

    def _build_exec_command(self) -> list[str]:
        """Build the codex exec argument list for one tagging run."""
        command = [
            self.settings.codex_command,
            "exec",
            "--json",
            "--skip-git-repo-check",
            "-C",
            self.settings.agent_cwd,
            "-s",
            self.settings.codex_sandbox,
            "-m",
            self.settings.codex_model,
            "-c",
            f'model_reasoning_effort="{self.settings.codex_reasoning_effort}"',
        ]
        if self.settings.codex_model_verbosity:
            command.extend(
                [
                    "-c",
                    f'model_verbosity="{self.settings.codex_model_verbosity}"',
                ],
            )
        if self.settings.codex_network_access:
            command.extend(["-c", "sandbox_workspace_write.network_access=true"])
        command.append("-")
        return command

    def _build_subprocess_env(self) -> dict[str, str]:
        """Return environment variables for the Codex subprocess."""
        env = os.environ.copy()
        env["CODEX_HOME"] = self.settings.codex_home
        if self.settings.codex_api_key:
            env["CODEX_API_KEY"] = self.settings.codex_api_key
        return env

    def _extract_text(self, payload: Any) -> str | None:
        """Extract human-readable text from a Codex JSON event payload."""
        if isinstance(payload, str) and payload.strip():
            return payload.strip()
        if not isinstance(payload, dict):
            return None

        error = payload.get("error")
        if isinstance(error, str) and error.strip():
            return error.strip()
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()

        for key in ("result", "message", "text", "content", "output"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        content = payload.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            if parts:
                return "\n".join(parts)
        return None

    def _extract_tool_event(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Return a normalized tool event from current and older Codex JSON shapes."""
        event_type = str(event.get("type", "")).lower()
        if event_type in {"tool_call", "tool_result", "tool"}:
            return event

        item = event.get("item")
        if not isinstance(item, dict):
            return None

        item_type = str(item.get("type", "")).lower()
        if item_type not in {"tool_call", "tool_result", "tool", "mcp_tool_call"}:
            return None

        normalized = dict(item)
        if "status" not in normalized and event_type.endswith(".completed"):
            normalized["status"] = "completed"
        return normalized

    def _log_codex_event(self, document_id: int, event: dict[str, Any]) -> str | None:
        """Log one Codex JSON event and return an error summary when present."""
        event_type = str(event.get("type", "")).lower()
        item = event.get("item")
        item_type = str(item.get("type", "")).lower() if isinstance(item, dict) else ""
        text = self._extract_text(item) or self._extract_text(event)

        if (
            event_type in {"assistant", "agent_message", "message"}
            or item_type in {"assistant_message", "message"}
        ) and text:
            logger.info("Agent assistant (document %s): %s", document_id, self._truncate_for_log(text))
            return None

        if (
            event_type in {"thinking", "reasoning"}
            or item_type in {"reasoning", "thinking"}
        ) and text:
            logger.info("Agent thinking (document %s): %s", document_id, self._truncate_for_log(text))
            return None

        tool_event = self._extract_tool_event(event)
        if tool_event is not None:
            server = tool_event.get("server") or tool_event.get("server_name")
            name = tool_event.get("name") or tool_event.get("tool") or "?"
            if server:
                name = f"{server}.{name}"
            status = str(tool_event.get("status", "completed")).lower()
            args = self._truncate_for_log(
                tool_event.get("args", tool_event.get("arguments", "")),
            )
            tool_text = self._extract_text(tool_event)
            raw_result = tool_event.get("result")
            if raw_result is None:
                raw_result = tool_event.get("output")
            if raw_result is None:
                raw_result = tool_text or ""
            result = self._truncate_for_log(raw_result)
            logger.info(
                "Agent tool %s (document %s) status=%s args=%s result=%s",
                name,
                document_id,
                status,
                args,
                result,
            )
            if status in {"error", "failed"}:
                return f"{name}: {result or 'tool call failed'}"
            return None

        if event_type in {"error", "run_error", "turn.failed"} or item_type == "error":
            return text or "Codex run failed"

        if event_type in {"status", "info"} and text:
            logger.info("Agent status (document %s): %s", document_id, text)
        return None

    def _parse_codex_output(
        self,
        document_id: int,
        stdout: str,
        stderr: str,
    ) -> tuple[str | None, str | None, list[str], int, int]:
        """Parse codex exec output and return summary, error, tool errors, counts."""
        summary: str | None = None
        error: str | None = None
        tool_errors: list[str] = []
        event_count = 0
        tool_count = 0

        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError:
                summary = stripped
                continue
            if not isinstance(event, dict):
                continue

            event_count += 1
            logger.debug("Codex raw event (document %s): %s", document_id, stripped)

            if self._extract_tool_event(event) is not None:
                tool_count += 1

            tool_error = self._log_codex_event(document_id, event)
            if tool_error:
                tool_errors.append(tool_error)

            event_type = str(event.get("type", "")).lower()
            item = event.get("item")
            item_type = str(item.get("type", "")).lower() if isinstance(item, dict) else ""
            text = self._extract_text(item) or self._extract_text(event)
            if (
                event_type in {"result", "final", "completed", "agent_message", "assistant"}
                or item_type in {"assistant_message", "message"}
            ) and text:
                summary = text
            if event_type in {"error", "run_error", "turn.failed"} or item_type == "error":
                error = text or "Codex run failed"

        if not error and stderr.strip():
            logger.info("Codex stderr (document %s): %s", document_id, self._truncate_for_log(stderr))

        if not error and tool_errors:
            error = "; ".join(tool_errors)
        return summary, error, tool_errors, event_count, tool_count

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
        run_id = str(uuid.uuid4())

        logger.info("Starting Codex agent for document %s", document_id)

        try:
            completed = subprocess.run(
                self._build_exec_command(),
                input=prompt,
                capture_output=True,
                text=True,
                env=self._build_subprocess_env(),
                check=False,
            )
        except FileNotFoundError as exc:
            logger.exception("Codex CLI not found for document %s", document_id)
            return TaggingResult(
                document_id=document_id,
                status="startup_error",
                error=str(exc),
            )
        except OSError as exc:
            logger.exception("Codex agent failed to start for document %s", document_id)
            return TaggingResult(
                document_id=document_id,
                status="startup_error",
                error=str(exc),
            )

        summary, error, _tool_errors, event_count, tool_count = self._parse_codex_output(
            document_id,
            completed.stdout,
            completed.stderr,
        )

        if completed.returncode != 0:
            error_message = error or completed.stderr.strip() or completed.stdout.strip()
            if not error_message:
                error_message = f"Codex exited with code {completed.returncode}"
            logger.error(
                "Codex agent run failed for document %s (run_id=%s): %s",
                document_id,
                run_id,
                error_message,
            )
            return TaggingResult(
                document_id=document_id,
                status="run_error",
                run_id=run_id,
                error=error_message,
            )

        if summary:
            logger.info(
                "Agent summary (document %s): %s",
                document_id,
                self._truncate_for_log(summary),
            )
        if event_count == 0:
            logger.warning(
                "Codex agent produced no JSON events for document %s (run_id=%s)",
                document_id,
                run_id,
            )
        elif tool_count == 0:
            logger.warning(
                "Codex agent finished without any tool calls for document %s (run_id=%s)",
                document_id,
                run_id,
            )
        logger.info("Codex agent finished for document %s (run_id=%s)", document_id, run_id)
        return TaggingResult(
            document_id=document_id,
            status="finished",
            run_id=run_id,
            summary=summary,
        )
