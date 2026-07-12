from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = Field(default="local", alias="SAFE_MIND_ENV")
    api_title: str = Field(default="SafeMind Backend", alias="SAFE_MIND_API_TITLE")
    emotional_filter_provider: Literal["heuristic", "openai"] = Field(
        default="openai",
        alias="SAFE_MIND_EMOTIONAL_FILTER_PROVIDER",
    )
    openai_emotional_filter_model: str = Field(
        default="gpt-4o-mini",
        alias="SAFE_MIND_OPENAI_EMOTIONAL_FILTER_MODEL",
    )
    psychological_analyzer_provider: Literal["heuristic", "openai"] = Field(
        default="openai",
        alias="SAFE_MIND_PSYCHOLOGICAL_ANALYZER_PROVIDER",
    )
    openai_psychological_analyzer_model: str = Field(
        default="gpt-4o-mini",
        alias="SAFE_MIND_OPENAI_PSYCHOLOGICAL_ANALYZER_MODEL",
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="SAFE_MIND_OPENAI_EMBEDDING_MODEL",
    )
    enable_embeddings: bool = Field(default=False, alias="SAFE_MIND_ENABLE_EMBEDDINGS")
    signal_store_provider: Literal["sqlite", "mongodb"] = Field(
        default="sqlite",
        alias="SAFE_MIND_SIGNAL_STORE_PROVIDER",
    )
    signal_db_path: str = Field(default="data/safe_mind_signals.sqlite3", alias="SAFE_MIND_SIGNAL_DB_PATH")
    vector_db_path: str = Field(default="data/safe_mind_vectors.sqlite3", alias="SAFE_MIND_VECTOR_DB_PATH")
    mongodb_uri: str | None = Field(default=None, alias="SAFE_MIND_MONGODB_URI")
    mongodb_database: str = Field(default="safe_mind", alias="SAFE_MIND_MONGODB_DATABASE")
    pipeline_version: str = Field(default="v1", alias="SAFE_MIND_PIPELINE_VERSION")
    persist_signals: bool = Field(default=True, alias="SAFE_MIND_PERSIST_SIGNALS")
    enable_eval_ui: bool = Field(default=True, alias="SAFE_MIND_ENABLE_EVAL_UI")
    eval_auth_username: str = Field(default="safemind", alias="SAFE_MIND_EVAL_AUTH_USERNAME")
    eval_auth_password: str | None = Field(default=None, alias="SAFE_MIND_EVAL_AUTH_PASSWORD")
    integration_api_token: str | None = Field(default=None, alias="SAFE_MIND_INTEGRATION_API_TOKEN")
    parent_contact_url_template: str | None = Field(default=None, alias="SAFE_MIND_PARENT_CONTACT_URL_TEMPLATE")
    parent_contact_token: str | None = Field(default=None, alias="SAFE_MIND_PARENT_CONTACT_TOKEN")
    whatsapp_access_token: str | None = Field(default=None, alias="SAFE_MIND_WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str | None = Field(default=None, alias="SAFE_MIND_WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_template_name: str | None = Field(default=None, alias="SAFE_MIND_WHATSAPP_TEMPLATE_NAME")
    whatsapp_template_language: str = Field(default="he", alias="SAFE_MIND_WHATSAPP_TEMPLATE_LANGUAGE")
    whatsapp_verification_template_name: str | None = Field(
        default="safe_mind_auth_code",
        alias="SAFE_MIND_WHATSAPP_VERIFICATION_TEMPLATE_NAME",
    )
    whatsapp_verification_template_language: str = Field(
        default="he",
        alias="SAFE_MIND_WHATSAPP_VERIFICATION_TEMPLATE_LANGUAGE",
    )
    whatsapp_graph_api_version: str = Field(default="v23.0", alias="SAFE_MIND_WHATSAPP_GRAPH_API_VERSION")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    def production_config_errors(self) -> list[str]:
        if self.env.lower() != "production":
            return []

        errors: list[str] = []
        if self.signal_store_provider != "mongodb":
            errors.append("SAFE_MIND_SIGNAL_STORE_PROVIDER must be mongodb in production.")
        if not self.mongodb_uri:
            errors.append("SAFE_MIND_MONGODB_URI is required in production.")
        if self.psychological_analyzer_provider == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required when the production analyzer provider is openai.")
        if self.enable_eval_ui and not self.eval_auth_password:
            errors.append("SAFE_MIND_EVAL_AUTH_PASSWORD is required in production.")
        if not self.integration_api_token:
            errors.append("SAFE_MIND_INTEGRATION_API_TOKEN is required in production.")
        if not self.whatsapp_access_token:
            errors.append("SAFE_MIND_WHATSAPP_ACCESS_TOKEN is required in production.")
        if not self.whatsapp_phone_number_id:
            errors.append("SAFE_MIND_WHATSAPP_PHONE_NUMBER_ID is required in production.")
        if not self.whatsapp_template_name:
            errors.append("SAFE_MIND_WHATSAPP_TEMPLATE_NAME is required in production.")
        if not self.whatsapp_verification_template_name:
            errors.append("SAFE_MIND_WHATSAPP_VERIFICATION_TEMPLATE_NAME is required in production.")
        return errors


def validate_production_settings() -> None:
    errors = settings.production_config_errors()
    if errors:
        raise RuntimeError("Invalid production configuration: " + " ".join(errors))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
