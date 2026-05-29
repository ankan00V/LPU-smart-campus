import os
import sys
from pathlib import Path

import pytest

from app.mongo import close_mongo


_TEST_DB_PATH = Path(__file__).resolve().parent.parent / ".lpu_tmp" / "pytest-collection.sqlite3"
_TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
os.environ["APP_RUNTIME_STRICT"] = "false"
os.environ["SQLALCHEMY_DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["REALTIME_BACKEND"] = "redis"
os.environ["REALTIME_BACKENDS"] = "redis"
os.environ["REALTIME_BACKENDS_REQUIRED"] = "false"
os.environ["SQL_OUTBOX_ENABLED"] = "false"
os.environ.pop("POSTGRES_ADMIN_DATABASE_URL", None)


@pytest.fixture(scope="function", autouse=True)
def _runtime_defaults_per_test():
    keys = (
        "APP_RUNTIME_STRICT",
        "MONGO_PERSISTENCE_REQUIRED",
        "MONGO_READ_PREFERRED",
        "MONGO_URI",
        "MONGODB_URI",
        "MONGO_URI_FALLBACK",
        "MONGODB_URI_FALLBACK",
        "MONGO_MONGITA_FALLBACK",
        "REDIS_REQUIRED",
        "REDIS_URL",
        "REALTIME_BACKEND",
        "REALTIME_BACKENDS",
        "REALTIME_BACKENDS_REQUIRED",
        "SQL_OUTBOX_ENABLED",
        "WORKER_REQUIRED",
        "WORKER_INLINE_FALLBACK_ENABLED",
        "STUDENT_AUTH_TURNSTILE_ENABLED",
        "STUDENT_AUTH_TURNSTILE_SITE_KEY",
        "STUDENT_AUTH_TURNSTILE_SECRET_KEY",
    )
    backup = {key: os.environ.get(key) for key in keys}

    os.environ["APP_RUNTIME_STRICT"] = "false"
    os.environ["MONGO_PERSISTENCE_REQUIRED"] = "false"
    os.environ["MONGO_READ_PREFERRED"] = "false"
    os.environ["MONGO_URI"] = ""
    os.environ["MONGODB_URI"] = ""
    os.environ["MONGO_URI_FALLBACK"] = ""
    os.environ["MONGODB_URI_FALLBACK"] = ""
    os.environ["MONGO_MONGITA_FALLBACK"] = "false"
    os.environ["REDIS_REQUIRED"] = "false"
    os.environ["REDIS_URL"] = ""
    os.environ["REALTIME_BACKEND"] = "redis"
    os.environ["REALTIME_BACKENDS"] = "redis"
    os.environ["REALTIME_BACKENDS_REQUIRED"] = "false"
    os.environ["SQL_OUTBOX_ENABLED"] = "false"
    os.environ["WORKER_REQUIRED"] = "false"
    os.environ["WORKER_INLINE_FALLBACK_ENABLED"] = "true"
    os.environ["STUDENT_AUTH_TURNSTILE_ENABLED"] = "true"
    os.environ["STUDENT_AUTH_TURNSTILE_SITE_KEY"] = "1x00000000000000000000AA"
    os.environ["STUDENT_AUTH_TURNSTILE_SECRET_KEY"] = "1x0000000000000000000000000000000AA"
    close_mongo()

    try:
        yield
    finally:
        close_mongo()
        for key, previous in backup.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
