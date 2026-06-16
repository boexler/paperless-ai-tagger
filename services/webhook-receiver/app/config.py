from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    prompt_template_path: str = Field(
        default="/app/prompts/tag-document.md",
        validation_alias="PROMPT_TEMPLATE_PATH",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    dedup_ttl_hours: int = Field(default=24, validation_alias="DEDUP_TTL_HOURS")
    data_dir: str = Field(default="/data", validation_alias="DATA_DIR")
    agent_cwd: str = Field(default="/app", validation_alias="AGENT_CWD")


settings = Settings()
