from safe_mind.core.config import Settings


def test_local_config_does_not_require_production_secrets() -> None:
    settings = Settings(_env_file=None, SAFE_MIND_ENV="local")

    assert settings.production_config_errors() == []


def test_production_config_requires_secrets() -> None:
    settings = Settings(
        _env_file=None,
        SAFE_MIND_ENV="production",
        SAFE_MIND_SIGNAL_STORE_PROVIDER="sqlite",
        SAFE_MIND_PSYCHOLOGICAL_ANALYZER_PROVIDER="openai",
    )

    errors = settings.production_config_errors()

    assert "SAFE_MIND_SIGNAL_STORE_PROVIDER must be mongodb in production." in errors
    assert "SAFE_MIND_MONGODB_URI is required in production." in errors
    assert "OPENAI_API_KEY is required when the production analyzer provider is openai." in errors
    assert "SAFE_MIND_EVAL_AUTH_PASSWORD is required in production." in errors
    assert "SAFE_MIND_INTEGRATION_API_TOKEN is required in production." in errors
    assert "SAFE_MIND_WHATSAPP_ACCESS_TOKEN is required in production." in errors
    assert "SAFE_MIND_WHATSAPP_PHONE_NUMBER_ID is required in production." in errors
    assert "SAFE_MIND_WHATSAPP_TEMPLATE_NAME is required in production." in errors


def test_complete_production_config_has_no_errors() -> None:
    settings = Settings(
        _env_file=None,
        SAFE_MIND_ENV="production",
        SAFE_MIND_SIGNAL_STORE_PROVIDER="mongodb",
        SAFE_MIND_MONGODB_URI="mongodb+srv://example.invalid/safe_mind",
        SAFE_MIND_PSYCHOLOGICAL_ANALYZER_PROVIDER="openai",
        OPENAI_API_KEY="sk-test",
        SAFE_MIND_EVAL_AUTH_PASSWORD="eval-secret",
        SAFE_MIND_INTEGRATION_API_TOKEN="ingest-secret",
        SAFE_MIND_WHATSAPP_ACCESS_TOKEN="whatsapp-secret",
        SAFE_MIND_WHATSAPP_PHONE_NUMBER_ID="123456789",
        SAFE_MIND_WHATSAPP_TEMPLATE_NAME="safe_mind_alert",
    )

    assert settings.production_config_errors() == []
