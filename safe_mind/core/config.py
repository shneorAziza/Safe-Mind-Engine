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
    eval_auth_username: str = Field(default="safemind", alias="SAFE_MIND_EVAL_AUTH_USERNAME")
    eval_auth_password: str | None = Field(default=None, alias="SAFE_MIND_EVAL_AUTH_PASSWORD")
    integration_api_token: str | None = Field(default=None, alias="SAFE_MIND_INTEGRATION_API_TOKEN")
    next_alert_callback_url: str | None = Field(default=None, alias="SAFE_MIND_NEXT_ALERT_CALLBACK_URL")
    next_alert_callback_token: str | None = Field(default=None, alias="SAFE_MIND_NEXT_ALERT_CALLBACK_TOKEN")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
