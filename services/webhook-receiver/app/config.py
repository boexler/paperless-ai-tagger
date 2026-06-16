from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_PROMPT_TEMPLATE = "tag-document.md"
DOCKER_PROMPTS_DIR = "/app/prompts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    webhook_secret: str = Field(validation_alias="WEBHOOK_SECRET")
    cursor_api_key: str = Field(validation_alias="CURSOR_API_KEY")
    cursor_model: str = Field(default="composer-2.5", validation_alias="CURSOR_MODEL")
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
    data_dir: str = Field(default="/data", validation_alias="DATA_DIR")
    agent_cwd: str = Field(default="/app", validation_alias="AGENT_CWD")

    @model_validator(mode="after")
    def resolve_prompt_template_path(self) -> "Settings":
        """Resolve prompt path from PROMPT_TEMPLATE when PROMPT_TEMPLATE_PATH is unset."""
        if self.prompt_template_path is None:
            object.__setattr__(
                self,
                "prompt_template_path",
                f"{DOCKER_PROMPTS_DIR}/{self.prompt_template}",
            )
        return self


settings = Settings()
