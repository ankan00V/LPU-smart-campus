import logging
import os
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .runtime_infra import is_remote_service_host, managed_services_required

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)
_AFTER_COMMIT_HOOKS_KEY = "smartcampus_after_commit_hooks"


def _strict_runtime_enabled() -> bool:
    raw = (os.getenv("APP_RUNTIME_STRICT", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        value = int(default)
    return max(minimum, value)


def _explicit_bool_env(name: str) -> bool | None:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return None
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


def _normalized_postgres_url(raw: str) -> str:
    value = str(raw or "").strip()
    if value.startswith("postgres://"):
        return f"postgresql+psycopg://{value[len('postgres://'):]}"
    if value.startswith("postgresql://") and not value.startswith("postgresql+"):
        return f"postgresql+psycopg://{value[len('postgresql://'):]}"
    return value


def _normalized_database_url() -> str:
    raw = (os.getenv("SQLALCHEMY_DATABASE_URL") or "").strip()
    if not raw:
        if _strict_runtime_enabled():
            raise RuntimeError(
                "APP_RUNTIME_STRICT=true requires SQLALCHEMY_DATABASE_URL to be set to a live PostgreSQL DSN."
            )
        raw = "sqlite:///./campus.db"
    if raw.startswith("postgres://") or (raw.startswith("postgresql://") and not raw.startswith("postgresql+")):
        raw = _normalized_postgres_url(raw)
    elif raw.startswith("sqlite:///./"):
        relative_path = raw[len("sqlite:///./") :]
        raw = f"sqlite:///{(PROJECT_ROOT / relative_path).resolve()}"
    elif raw.startswith("sqlite:///") and not raw.startswith("sqlite:////"):
        suffix = raw[len("sqlite:///") :]
        if suffix and not suffix.startswith("/"):
            raw = f"sqlite:///{(PROJECT_ROOT / suffix).resolve()}"

    if _strict_runtime_enabled() and not raw.startswith("postgresql"):
        raise RuntimeError(
            "APP_RUNTIME_STRICT=true requires SQLALCHEMY_DATABASE_URL to point to PostgreSQL."
        )
    return raw


def _normalized_admin_database_url() -> str | None:
    raw = (
        os.getenv("POSTGRES_ADMIN_DATABASE_URL")
        or os.getenv("POSTGRES_TARGET_DATABASE_URL")
        or SQLALCHEMY_DATABASE_URL
    )
    normalized = _normalized_postgres_url(str(raw or "").strip())
    if not normalized.startswith("postgresql"):
        return None
    return normalized


def postgres_libpq_url(raw: str | None) -> str | None:
    value = str(raw or "").strip()
    if not value:
        return None
    if value.startswith("postgresql+"):
        prefix, remainder = value.split("://", 1)
        backend = prefix.split("+", 1)[0]
        return f"{backend}://{remainder}"
    return value


def _database_ssl_mode() -> str | None:
    safe_url = make_url(SQLALCHEMY_DATABASE_URL)
    env_mode = (os.getenv("DATABASE_SSL_MODE") or "").strip().lower()
    if env_mode:
        return env_mode
    query_mode = str(safe_url.query.get("sslmode") or "").strip().lower()
    if query_mode:
        return query_mode
    if managed_services_required():
        return "require"
    return None


def _database_tls_enabled() -> bool:
    mode = str(_database_ssl_mode() or "").strip().lower()
    return mode in {"require", "verify-ca", "verify-full"}


def _database_application_name() -> str | None:
    value = (os.getenv("DATABASE_APPLICATION_NAME") or "lpu-smart-campus-api").strip()
    return value or None


SQLALCHEMY_DATABASE_URL = _normalized_database_url()
POSTGRES_ADMIN_DATABASE_URL = _normalized_admin_database_url()
POSTGRES_ADMIN_LIBPQ_URL = postgres_libpq_url(POSTGRES_ADMIN_DATABASE_URL)
_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")
_is_postgresql = SQLALCHEMY_DATABASE_URL.startswith("postgresql")


def _database_pooler_host() -> bool:
    if not _is_postgresql:
        return False
    safe_url = make_url(SQLALCHEMY_DATABASE_URL)
    host = str(safe_url.host or "").strip().lower()
    if not host:
        return False
    return "-pooler." in host or ".pooler." in host or "pgbouncer" in host


def _database_disable_prepared_statements() -> bool:
    explicit = _explicit_bool_env("DATABASE_DISABLE_PREPARED_STATEMENTS")
    if explicit is not None:
        return explicit
    return _database_pooler_host()


def _engine_options() -> dict:
    if _is_sqlite:
        return {
            "connect_args": {"check_same_thread": False},
        }

    connect_args: dict[str, object] = {}
    if _is_postgresql:
        connect_args["connect_timeout"] = _env_int("DATABASE_CONNECT_TIMEOUT_SECONDS", 10, minimum=1)
        ssl_mode = _database_ssl_mode()
        if ssl_mode:
            connect_args["sslmode"] = ssl_mode

        ssl_root_cert = (os.getenv("DATABASE_SSL_ROOT_CERT") or "").strip()
        ssl_cert = (os.getenv("DATABASE_SSL_CERT") or "").strip()
        ssl_key = (os.getenv("DATABASE_SSL_KEY") or "").strip()
        if ssl_root_cert:
            connect_args["sslrootcert"] = ssl_root_cert
        if ssl_cert:
            connect_args["sslcert"] = ssl_cert
        if ssl_key:
            connect_args["sslkey"] = ssl_key

        statement_timeout_ms = _env_int("DATABASE_STATEMENT_TIMEOUT_MS", 0, minimum=0)
        if statement_timeout_ms > 0:
            connect_args["options"] = f"-c statement_timeout={statement_timeout_ms}"

        application_name = _database_application_name()
        if application_name:
            connect_args["application_name"] = application_name
        if _database_disable_prepared_statements():
            # Pooled PostgreSQL endpoints (for example PgBouncer/Neon poolers) are safer
            # when psycopg automatic prepared statements are disabled.
            connect_args["prepare_threshold"] = None

    return {
        "connect_args": connect_args,
        "pool_pre_ping": True,
        "pool_size": _env_int("DATABASE_POOL_SIZE", 10, minimum=1),
        "max_overflow": _env_int("DATABASE_MAX_OVERFLOW", 20, minimum=0),
        "pool_timeout": _env_int("DATABASE_POOL_TIMEOUT_SECONDS", 30, minimum=1),
        "pool_recycle": _env_int("DATABASE_POOL_RECYCLE_SECONDS", 1800, minimum=30),
    }


def database_status() -> dict:
    safe_url = make_url(SQLALCHEMY_DATABASE_URL)
    backend = str(safe_url.get_backend_name() or "").strip().lower() or "unknown"
    driver = str(safe_url.get_driver_name() or "").strip().lower() or None
    database = None
    host = None
    ssl_mode = None
    tls_enabled = False
    remote_host = False
    pooler_host = False
    prepared_statements_disabled = False
    if backend == "sqlite":
        database = str(safe_url.database or "")
    else:
        database = str(safe_url.database or "")
        host = str(safe_url.host or "") or None
        remote_host = is_remote_service_host(host)
        if backend == "postgresql":
            ssl_mode = _database_ssl_mode()
            tls_enabled = _database_tls_enabled()
            pooler_host = _database_pooler_host()
            prepared_statements_disabled = _database_disable_prepared_statements()

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        connected = True
        error = None
    except Exception as exc:  # noqa: BLE001
        connected = False
        error = str(exc)

    return {
        "backend": backend,
        "driver": driver,
        "database": database,
        "host": host,
        "remote_host": remote_host,
        "ssl_mode": ssl_mode,
        "tls_enabled": tls_enabled,
        "pooler_host": pooler_host,
        "prepared_statements_disabled": prepared_statements_disabled,
        "connected": connected,
        "error": error,
    }


def add_after_commit_hook(db: Session, callback: Callable[[], None]) -> None:
    hooks = db.info.setdefault(_AFTER_COMMIT_HOOKS_KEY, [])
    hooks.append(callback)


def _drain_after_commit_hooks(session: Session) -> list[Callable[[], None]]:
    hooks = session.info.pop(_AFTER_COMMIT_HOOKS_KEY, [])
    if not isinstance(hooks, list):
        return []
    return [hook for hook in hooks if callable(hook)]


@event.listens_for(Session, "after_commit")
def _run_after_commit_hooks(session: Session) -> None:
    for callback in _drain_after_commit_hooks(session):
        try:
            callback()
        except Exception:  # noqa: BLE001
            logger.exception("After-commit hook failed.")


@event.listens_for(Session, "after_rollback")
@event.listens_for(Session, "after_soft_rollback")
def _clear_after_commit_hooks(session: Session, *_args) -> None:
    session.info.pop(_AFTER_COMMIT_HOOKS_KEY, None)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    **_engine_options(),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
