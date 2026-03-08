import os
from pathlib import Path

import pytest


_TEST_DB_PATH = Path(__file__).resolve().parent.parent / ".codex_tmp" / "pytest-collection.sqlite3"
_TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
os.environ["APP_RUNTIME_STRICT"] = "false"
os.environ["SQLALCHEMY_DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ.pop("POSTGRES_ADMIN_DATABASE_URL", None)


@pytest.fixture(scope="function", autouse=True)
def _runtime_defaults_per_test():
    keys = (
        "APP_RUNTIME_STRICT",
        "MONGO_PERSISTENCE_REQUIRED",
        "MONGO_READ_PREFERRED",
        "REDIS_REQUIRED",
        "REDIS_URL",
        "WORKER_REQUIRED",
        "WORKER_INLINE_FALLBACK_ENABLED",
    )
    backup = {key: os.environ.get(key) for key in keys}

    os.environ["APP_RUNTIME_STRICT"] = "false"
    os.environ["MONGO_PERSISTENCE_REQUIRED"] = "false"
    os.environ["MONGO_READ_PREFERRED"] = "false"
    os.environ["REDIS_REQUIRED"] = "false"
    os.environ["REDIS_URL"] = ""
    os.environ["WORKER_REQUIRED"] = "false"
    os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "true"

    try:
        yield
    finally:
        for key, previous in backup.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
