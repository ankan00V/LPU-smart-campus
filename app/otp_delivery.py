import os
import smtplib
import ssl
import json
from email.message import EmailMessage
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv


_ENV_LOADED = False
_OTP_DELIVERY_MODES = {"smtp", "graph"}


def _ensure_env_loaded() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    _ENV_LOADED = True


def _delivery_mode() -> str:
    _ensure_env_loaded()
    return (os.getenv("OTP_DELIVERY_MODE", "smtp").strip().lower() or "smtp")


def otp_delivery_mode() -> str:
    mode = _delivery_mode()
    if mode not in _OTP_DELIVERY_MODES:
        raise RuntimeError("Invalid OTP_DELIVERY_MODE. Use 'smtp' or 'graph'.")
    return mode


def _smtp_host() -> str:
    _ensure_env_loaded()
    return os.getenv("OTP_SMTP_HOST", "").strip()


def _smtp_port() -> int:
    _ensure_env_loaded()
    raw = os.getenv("OTP_SMTP_PORT", "587").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError("OTP_SMTP_PORT must be a valid integer port.") from exc
    if value < 1 or value > 65535:
        raise RuntimeError("OTP_SMTP_PORT must be between 1 and 65535.")
    return value


def _smtp_username() -> str:
    _ensure_env_loaded()
    return os.getenv("OTP_SMTP_USERNAME", "").strip()


def _smtp_password() -> str:
    _ensure_env_loaded()
    raw = os.getenv("OTP_SMTP_PASSWORD", "").strip()
    compact = raw.replace(" ", "")
    # Gmail app passwords are often copied as 4 groups with spaces (xxxx xxxx xxxx xxxx).
    # Normalize that format to avoid false auth failures from pasted spacing.
    if raw != compact and len(compact) == 16 and compact.isalnum():
        return compact
    return raw


def _smtp_use_ssl() -> bool:
    _ensure_env_loaded()
    return os.getenv("OTP_SMTP_USE_SSL", "false").strip().lower() in {"1", "true", "yes"}


def _smtp_starttls() -> bool:
    _ensure_env_loaded()
    return os.getenv("OTP_SMTP_STARTTLS", "true").strip().lower() in {"1", "true", "yes"}


def _from_email() -> str:
    _ensure_env_loaded()
    return os.getenv("OTP_FROM_EMAIL", "").strip() or _smtp_username()


def _subject_prefix() -> str:
    _ensure_env_loaded()
    return os.getenv("OTP_SUBJECT_PREFIX", "LPU Smart Campus").strip() or "LPU Smart Campus"


def otp_expiry_minutes() -> int:
    _ensure_env_loaded()
    raw = os.getenv("OTP_EXPIRES_MINUTES", "10").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 10
    return max(3, min(30, value))


def _otp_mail_subject() -> str:
    return f"{_subject_prefix()} | Your OTP Code"


def _otp_mail_body(otp_code: str) -> str:
    expiry_minutes = otp_expiry_minutes()
    return "\n".join(
        [
            "Your one-time password (OTP) for LPU Smart Campus login is:",
            "",
            f"{otp_code}",
            "",
            f"This OTP expires in {expiry_minutes} minutes.",
            "If you did not request this, ignore this email.",
        ]
    )


def _build_message(destination_email: str, *, subject: str, body: str) -> EmailMessage:
    recipient = str(destination_email or "").strip()
    clean_subject = str(subject or "").strip()
    clean_body = str(body or "").strip()
    if not recipient:
        raise RuntimeError("Destination email is required.")
    if not clean_subject:
        raise RuntimeError("Email subject is required.")
    if not clean_body:
        raise RuntimeError("Email body is required.")

    message = EmailMessage()
    message["From"] = _from_email()
    message["To"] = recipient
    message["Subject"] = clean_subject
    message.set_content(clean_body)
    return message


def _ensure_smtp_config() -> None:
    def is_placeholder(value: str) -> bool:
        return value.strip() in {
            "",
            "CHANGE_ME",
            "YOUR_SENDER_GMAIL@gmail.com",
            "YOUR_GMAIL_APP_PASSWORD",
            "your_sender_gmail@gmail.com",
            "your_gmail_app_password",
            "your_mailbox_password_or_app_password",
        }

    missing: list[str] = []
    if is_placeholder(_smtp_host()):
        missing.append("OTP_SMTP_HOST")
    if is_placeholder(_smtp_username()):
        missing.append("OTP_SMTP_USERNAME")
    if is_placeholder(_smtp_password()):
        missing.append("OTP_SMTP_PASSWORD")
    if is_placeholder(_from_email()):
        missing.append("OTP_FROM_EMAIL")
    if missing:
        raise RuntimeError(f"OTP SMTP is not configured. Missing: {', '.join(missing)}")
    if _smtp_use_ssl() and _smtp_starttls():
        raise RuntimeError("OTP SMTP config is invalid. Enable either SSL or STARTTLS, not both.")


def _verify_smtp_connection() -> None:
    _ensure_smtp_config()
    host = _smtp_host()
    port = _smtp_port()
    username = _smtp_username()
    password = _smtp_password()
    try:
        if _smtp_use_ssl():
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
                server.login(username, password)
                code, _ = server.noop()
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                if _smtp_starttls():
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                server.login(username, password)
                code, _ = server.noop()
        if int(code) != 250:
            raise RuntimeError(f"SMTP server health probe returned unexpected status code {code}.")
    except (OSError, smtplib.SMTPException, RuntimeError) as exc:
        raise RuntimeError(f"OTP SMTP verification failed: {exc}") from exc


def _send_smtp_message(destination_email: str, *, subject: str, body: str) -> None:
    _ensure_smtp_config()
    message = _build_message(destination_email, subject=subject, body=body)

    host = _smtp_host()
    port = _smtp_port()
    username = _smtp_username()
    password = _smtp_password()

    if _smtp_use_ssl():
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as server:
            server.login(username, password)
            server.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=15) as server:
        if _smtp_starttls():
            context = ssl.create_default_context()
            server.starttls(context=context)
        server.login(username, password)
        server.send_message(message)


def _send_via_smtp(destination_email: str, otp_code: str) -> None:
    _send_smtp_message(
        destination_email,
        subject=_otp_mail_subject(),
        body=_otp_mail_body(otp_code),
    )


def _graph_tenant_id() -> str:
    _ensure_env_loaded()
    return os.getenv("OTP_GRAPH_TENANT_ID", "").strip()


def _graph_client_id() -> str:
    _ensure_env_loaded()
    return os.getenv("OTP_GRAPH_CLIENT_ID", "").strip()


def _graph_client_secret() -> str:
    _ensure_env_loaded()
    return os.getenv("OTP_GRAPH_CLIENT_SECRET", "").strip()


def _graph_sender_user() -> str:
    _ensure_env_loaded()
    return os.getenv("OTP_GRAPH_SENDER_USER", "").strip() or _from_email()


def _ensure_graph_config() -> None:
    missing: list[str] = []
    if not _graph_tenant_id():
        missing.append("OTP_GRAPH_TENANT_ID")
    if not _graph_client_id():
        missing.append("OTP_GRAPH_CLIENT_ID")
    if not _graph_client_secret():
        missing.append("OTP_GRAPH_CLIENT_SECRET")
    if not _graph_sender_user():
        missing.append("OTP_GRAPH_SENDER_USER")
    if missing:
        raise RuntimeError(f"OTP Graph is not configured. Missing: {', '.join(missing)}")


def _graph_access_token() -> str:
    _ensure_graph_config()
    token_url = f"https://login.microsoftonline.com/{_graph_tenant_id()}/oauth2/v2.0/token"
    body = urlencode(
        {
            "client_id": _graph_client_id(),
            "client_secret": _graph_client_secret(),
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
    ).encode("utf-8")
    request = Request(token_url, data=body, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
            token = payload.get("access_token")
            if not token:
                raise RuntimeError("Graph token response missing access_token")
            return str(token)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        raise RuntimeError(f"Graph token request failed: HTTP {exc.code} {raw}") from exc


def _send_graph_message(destination_email: str, *, subject: str, body: str) -> None:
    token = _graph_access_token()
    sender_user = quote(_graph_sender_user())
    send_url = f"https://graph.microsoft.com/v1.0/users/{sender_user}/sendMail"

    payload = {
        "message": {
            "subject": str(subject or "").strip(),
            "body": {"contentType": "Text", "content": str(body or "").strip()},
            "toRecipients": [{"emailAddress": {"address": destination_email}}],
        },
        "saveToSentItems": False,
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(send_url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(request, timeout=20):
            return
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        raise RuntimeError(f"Graph sendMail failed: HTTP {exc.code} {raw}") from exc


def _send_via_graph(destination_email: str, otp_code: str) -> None:
    _send_graph_message(
        destination_email,
        subject=_otp_mail_subject(),
        body=_otp_mail_body(otp_code),
    )


def _verify_graph_connection() -> None:
    token = _graph_access_token()
    sender_user = quote(_graph_sender_user())
    check_url = f"https://graph.microsoft.com/v1.0/users/{sender_user}?$select=id,mail,userPrincipalName"
    request = Request(check_url, method="GET")
    request.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        raise RuntimeError(f"OTP Graph verification failed: HTTP {exc.code} {raw}") from exc
    except OSError as exc:
        raise RuntimeError(f"OTP Graph verification failed: {exc}") from exc
    if not payload.get("id"):
        raise RuntimeError("OTP Graph verification failed: sender user lookup returned no id.")


def assert_otp_delivery_ready(*, verify_connection: bool = False) -> str:
    mode = otp_delivery_mode()
    if mode == "smtp":
        _ensure_smtp_config()
        if verify_connection:
            _verify_smtp_connection()
        return mode
    if mode == "graph":
        _ensure_graph_config()
        if verify_connection:
            _verify_graph_connection()
        return mode
    raise RuntimeError("Invalid OTP_DELIVERY_MODE. Use 'smtp' or 'graph'.")


def send_login_otp(destination_email: str, otp_code: str) -> dict:
    return send_transactional_email(
        destination_email,
        subject=_otp_mail_subject(),
        body=_otp_mail_body(otp_code),
    )


def send_transactional_email(destination_email: str, *, subject: str, body: str) -> dict:
    if not str(destination_email or "").strip():
        raise RuntimeError("Destination email is required.")
    if not str(subject or "").strip():
        raise RuntimeError("Email subject is required.")
    if not str(body or "").strip():
        raise RuntimeError("Email body is required.")

    mode = otp_delivery_mode()

    if mode == "smtp":
        _send_smtp_message(destination_email, subject=subject, body=body)
        return {
            "channel": "smtp-email",
        }

    if mode == "graph":
        _send_graph_message(destination_email, subject=subject, body=body)
        return {
            "channel": "graph-email",
        }

    raise RuntimeError("Invalid OTP_DELIVERY_MODE. Use 'smtp' or 'graph'.")
