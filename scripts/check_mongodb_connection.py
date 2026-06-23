from safe_mind.core.config import settings
from safe_mind.storage.factory import get_signal_store


def main() -> None:
    if settings.signal_store_provider != "mongodb":
        raise SystemExit("SAFE_MIND_SIGNAL_STORE_PROVIDER is not set to mongodb.")

    store = get_signal_store()
    store.initialize()
    print({"provider": "mongodb", "database": settings.mongodb_database, "records": store.count()})


if __name__ == "__main__":
    main()
