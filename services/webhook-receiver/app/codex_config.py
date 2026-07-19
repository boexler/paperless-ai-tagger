import json
from pathlib import Path

from app.config import Settings


def _toml_string(value: str) -> str:
    """Return a TOML-safe double-quoted string."""
    return json.dumps(value, ensure_ascii=False)


def build_codex_config_content(settings: Settings) -> str:
    """Build Codex CLI config.toml with Paperless MCP and runtime defaults."""
    lines = [
        f"model = {_toml_string(settings.codex_model)}",
        f"model_reasoning_effort = {_toml_string(settings.codex_reasoning_effort)}",
        f"approval_policy = {_toml_string(settings.codex_approval_policy)}",
        f"sandbox_mode = {_toml_string(settings.codex_sandbox)}",
    ]
    if settings.codex_model_verbosity:
        lines.append(
            f"model_verbosity = {_toml_string(settings.codex_model_verbosity)}",
        )

    lines.extend(
        [
            "",
            "[sandbox_workspace_write]",
            f"network_access = {'true' if settings.codex_network_access else 'false'}",
            "",
            "[mcp_servers.paperless]",
            f"command = {_toml_string(settings.paperless_mcp_command)}",
            'args = ["mcp"]',
            "",
            "[mcp_servers.paperless.env]",
            f"PAPERLESS_URL = {_toml_string(settings.paperless_url)}",
            f"PAPERLESS_TOKEN = {_toml_string(settings.paperless_api_token)}",
            "",
        ],
    )
    return "\n".join(lines)


def write_codex_config(settings: Settings) -> Path:
    """Write Codex config.toml under CODEX_HOME and return its path."""
    codex_home = Path(settings.codex_home)
    codex_home.mkdir(parents=True, exist_ok=True)
    config_path = codex_home / "config.toml"
    config_path.write_text(build_codex_config_content(settings), encoding="utf-8")
    return config_path
