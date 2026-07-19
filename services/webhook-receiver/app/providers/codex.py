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
            "--cd",
            self.settings.agent_cwd,
            "-a",
            self.settings.codex_approval_policy,
            "-s",
            self.settings.codex_sandbox,
            "-c",
            f"model={self.settings.codex_model}",
            "-c",
            f"model_reasoning_effort={self.settings.codex_reasoning_effort}",
        ]
        if self.settings.codex_model_verbosity:
            command.extend(
                ["-c", f"model_verbosity={self.settings.codex_model_verbosity}"],
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

    def _log_codex_event(self, document_id: int, event: dict[str, Any]) -> str | None:
        """Log one Codex JSON event and return an error summary when present."""
        event_type = str(event.get("type", "")).lower()
        text = self._extract_text(event)

        if event_type in {"assistant", "agent_message", "message"} and text:
            logger.info("Agent assistant (document %s): %s", document_id, self._truncate_for_log(text))
            return None

        if event_type in {"thinking", "reasoning"} and text:
            logger.info("Agent thinking (document %s): %s", document_id, self._truncate_for_log(text))
            return None

        if event_type in {"tool_call", "tool_result", "tool"}:
            name = event.get("name") or event.get("tool") or "?"
            status = str(event.get("status", "completed")).lower()
            args = self._truncate_for_log(event.get("args", event.get("arguments", "")))
            result = self._truncate_for_log(event.get("result", text or ""))
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

        if event_type in {"error", "run_error"}:
            return text or "Codex run failed"

        if event_type in {"status", "info"} and text:
            logger.info("Agent status (document %s): %s", document_id, text)
        return None

    def _parse_codex_output(
        self,
        document_id: int,
        stdout: str,
        stderr: str,
    ) -> tuple[str | None, str | None, list[str]]:
        """Parse codex exec output and return summary, error, and tool errors."""
        summary: str | None = None
        error: str | None = None
        tool_errors: list[str] = []

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

            tool_error = self._log_codex_event(document_id, event)
            if tool_error:
                tool_errors.append(tool_error)

            event_type = str(event.get("type", "")).lower()
            text = self._extract_text(event)
            if event_type in {"result", "final", "completed", "agent_message", "assistant"} and text:
                summary = text
            if event_type in {"error", "run_error"}:
                error = text or "Codex run failed"

        if not error and stderr.strip():
            logger.info("Codex stderr (document %s): %s", document_id, self._truncate_for_log(stderr))

        if not error and tool_errors:
            error = "; ".join(tool_errors)
        return summary, error, tool_errors

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

        summary, error, _tool_errors = self._parse_codex_output(
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
        logger.info("Codex agent finished for document %s (run_id=%s)", document_id, run_id)
        return TaggingResult(
            document_id=document_id,
            status="finished",
            run_id=run_id,
            summary=summary,
        )
