from functools import lru_cache
from typing import Literal, Self

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.model_params import parse_cursor_model_params

DEFAULT_PROMPT_TEMPLATE = "01-tag-document.md"
DOCKER_PROMPTS_DIR = "/app/prompts"
AGENT_PROVIDERS = ("cursor", "codex")
CODEX_REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")
CODEX_APPROVAL_POLICIES = ("untrusted", "on-request", "on-failure", "never")
CODEX_SANDBOX_MODES = ("read-only", "workspace-write", "danger-full-access")
CODEX_MODEL_VERBOSITIES = ("low", "medium", "high")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    webhook_secret: str = Field(validation_alias="WEBHOOK_SECRET")
    agent_provider: Literal["cursor", "codex"] = Field(
        default="cursor",
        validation_alias="AGENT_PROVIDER",
    )
    cursor_api_key: str | None = Field(default=None, validation_alias="CURSOR_API_KEY")
    cursor_model: str = Field(default="composer-2.5", validation_alias="CURSOR_MODEL")
    cursor_model_params: str = Field(
        default="fast:false",
        validation_alias="CURSOR_MODEL_PARAMS",
    )
    cursor_list_models_on_startup: bool = Field(
        default=False,
        validation_alias="CURSOR_LIST_MODELS_ON_STARTUP",
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "CODEX_API_KEY"),
    )
    codex_command: str = Field(default="codex", validation_alias="CODEX_COMMAND")
    codex_model: str = Field(default="gpt-5.4-mini", validation_alias="CODEX_MODEL")
    codex_reasoning_effort: str = Field(
        default="low",
        validation_alias="CODEX_REASONING_EFFORT",
    )
    codex_model_verbosity: str | None = Field(
        default="low",
        validation_alias="CODEX_MODEL_VERBOSITY",
    )
    codex_approval_policy: str = Field(
        default="never",
        validation_alias="CODEX_APPROVAL_POLICY",
    )
    codex_sandbox: str = Field(
        default="workspace-write",
        validation_alias="CODEX_SANDBOX",
    )
    codex_network_access: bool = Field(
        default=True,
        validation_alias="CODEX_NETWORK_ACCESS",
    )
    codex_home: str = Field(default="/data/codex", validation_alias="CODEX_HOME")
    paperless_url: str = Field(
        validation_alias=AliasChoices("PAPERLESS_URL", "PAPERLESS_BASE_URL"),
    )
    paperless_api_token: str = Field(
        validation_alias=AliasChoices("PAPERLESS_TOKEN", "PAPERLESS_API_TOKEN"),
    )
    paperless_mcp_command: str = Field(
        default="/usr/local/bin/paperless-ngx-mcp",
        validation_alias="PAPERLESS_MCP_COMMAND",
    )
    prompt_template: str = Field(
        default=DEFAULT_PROMPT_TEMPLATE,
        validation_alias="PROMPT_TEMPLATE",
    )
    prompt_template_path: str | None = Field(
        default=None,
        validation_alias="PROMPT_TEMPLATE_PATH",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    dedup_ttl_hours: int = Field(default=24, validation_alias="DEDUP_TTL_HOURS")
    max_concurrent_jobs: int = Field(default=1, validation_alias="MAX_CONCURRENT_JOBS")
    data_dir: str = Field(default="/data", validation_alias="DATA_DIR")
    agent_cwd: str = Field(default="/app", validation_alias="AGENT_CWD")

    @field_validator("cursor_model_params")
    @classmethod
    def validate_cursor_model_params(cls, value: str) -> str:
        """Reject malformed CURSOR_MODEL_PARAMS at startup."""
        parse_cursor_model_params(value)
        return value

    @field_validator("codex_reasoning_effort")
    @classmethod
    def validate_codex_reasoning_effort(cls, value: str) -> str:
        """Reject unsupported Codex reasoning effort values at startup."""
        normalized = value.strip().lower()
        if normalized not in CODEX_REASONING_EFFORTS:
            allowed = ", ".join(CODEX_REASONING_EFFORTS)
            raise ValueError(
                f"Invalid CODEX_REASONING_EFFORT {value!r}: expected one of {allowed}",
            )
        return normalized

    @field_validator("codex_approval_policy")
    @classmethod
    def validate_codex_approval_policy(cls, value: str) -> str:
        """Reject unsupported Codex approval policies at startup."""
        normalized = value.strip().lower()
        if normalized not in CODEX_APPROVAL_POLICIES:
            allowed = ", ".join(CODEX_APPROVAL_POLICIES)
            raise ValueError(
                f"Invalid CODEX_APPROVAL_POLICY {value!r}: expected one of {allowed}",
            )
        return normalized

    @field_validator("codex_sandbox")
    @classmethod
    def validate_codex_sandbox(cls, value: str) -> str:
        """Reject unsupported Codex sandbox modes at startup."""
        normalized = value.strip().lower()
        if normalized not in CODEX_SANDBOX_MODES:
            allowed = ", ".join(CODEX_SANDBOX_MODES)
            raise ValueError(
                f"Invalid CODEX_SANDBOX {value!r}: expected one of {allowed}",
            )
        return normalized

    @field_validator("codex_model_verbosity")
    @classmethod
    def validate_codex_model_verbosity(cls, value: str | None) -> str | None:
        """Reject unsupported Codex verbosity values at startup."""
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        normalized = stripped.lower()
        if normalized not in CODEX_MODEL_VERBOSITIES:
            allowed = ", ".join(CODEX_MODEL_VERBOSITIES)
            raise ValueError(
                f"Invalid CODEX_MODEL_VERBOSITY {value!r}: expected one of {allowed}",
            )
        return normalized

    @model_validator(mode="after")
    def resolve_prompt_template_path(self) -> Self:
        """Resolve prompt path from PROMPT_TEMPLATE when PROMPT_TEMPLATE_PATH is unset."""
        if self.prompt_template_path is None:
            object.__setattr__(
                self,
                "prompt_template_path",
                f"{DOCKER_PROMPTS_DIR}/{self.prompt_template}",
            )
        return self

    @model_validator(mode="after")
    def validate_provider_credentials(self) -> Self:
        """Require provider-specific credentials based on AGENT_PROVIDER."""
        if self.agent_provider == "cursor" and not self.cursor_api_key:
            raise ValueError("CURSOR_API_KEY is required when AGENT_PROVIDER=cursor")
        if self.agent_provider == "codex" and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY (or CODEX_API_KEY) is required when AGENT_PROVIDER=codex",
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Load and cache application settings from the environment."""
    return Settings()
