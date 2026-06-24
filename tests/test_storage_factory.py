import pytest

from safe_mind.storage.factory import _get_signal_store
from safe_mind.storage.mongo_store import MongoSignalStore


def test_signal_store_is_cached_for_same_configuration() -> None:
    _get_signal_store.cache_clear()

    first = _get_signal_store(
        "local",
        "mongodb",
        "mongodb://example.invalid",
        "safe_mind",
        "unused.sqlite3",
    )
    second = _get_signal_store(
        "local",
        "mongodb",
        "mongodb://example.invalid",
        "safe_mind",
        "unused.sqlite3",
    )

    assert first is second
    assert isinstance(first, MongoSignalStore)


def test_sqlite_is_rejected_in_production() -> None:
    _get_signal_store.cache_clear()

    with pytest.raises(RuntimeError, match="must be mongodb in production"):
        _get_signal_store(
            "production",
            "sqlite",
            None,
            "safe_mind",
            "data/safe_mind.sqlite3",
        )
