from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .enterprise_controls import resolve_secret


def recovery_ai_email_enabled() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    raw = (os.getenv("RECOVERY_LLM_EMAIL_ENABLED", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _recovery_llm_provider() -> str:
    explicit = str(os.getenv("RECOVERY_LLM_PROVIDER") or "").strip().lower()
    if explicit:
        return explicit
    if _bedrock_bearer_tokens():
        return "bedrock"
    if str(resolve_secret("OPENROUTER_API_KEY", default="") or "").strip():
        return "openrouter"
    if str(resolve_secret("GEMINI_API_KEY", default="") or "").strip():
        return "gemini"
    return ""


def _recovery_llm_required() -> bool:
    raw = (os.getenv("RECOVERY_LLM_REQUIRED", "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _request_timeout_seconds() -> float:
    return _float_env("RECOVERY_LLM_REQUEST_TIMEOUT_SECONDS", 6.0, minimum=1.0, maximum=20.0)


def _total_timeout_seconds() -> float:
    return _float_env("RECOVERY_LLM_TOTAL_TIMEOUT_SECONDS", 14.0, minimum=2.0, maximum=30.0)


def _bedrock_region() -> str:
    raw = (
        str(resolve_secret("RECOVERY_BEDROCK_REGION", default="") or "").strip()
        or str(resolve_secret("COPILOT_BEDROCK_REGION", default="") or "").strip()
        or str(os.getenv("AWS_REGION") or "").strip()
        or "us-east-1"
    )
    return raw


def _bedrock_model_id(kind: str) -> str:
    # Use a safe default that is generally available for Converse.
    default = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    specific = str(resolve_secret(f"RECOVERY_BEDROCK_{kind}_MODEL_ID", default="") or "").strip()
    if specific:
        return specific
    generic = str(resolve_secret("RECOVERY_BEDROCK_MODEL_ID", default="") or "").strip()
    if generic:
        return generic
    copilot = str(resolve_secret("COPILOT_BEDROCK_MODEL_ID", default="") or "").strip()
    return copilot or default


def _bedrock_bearer_tokens() -> list[str]:
    tokens: list[str] = []
    # Preferred: AWS_BEARER_TOKEN_BEDROCK (official env var for Bedrock API keys)
    primary = str(resolve_secret("AWS_BEARER_TOKEN_BEDROCK", default="") or "").strip()
    if primary:
        tokens.append(primary)
    # Project-scoped aliases (optional)
    for name in ("RECOVERY_BEDROCK_API_KEY", "COPILOT_BEDROCK_API_KEY"):
        value = str(resolve_secret(name, default="") or "").strip()
        if value:
            tokens.append(value)
    # De-dupe
    out: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _extract_bedrock_text(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if not isinstance(output, dict):
        return ""
    message = output.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _bedrock_converse_text(*, model_id: str, system: str, user: str, deadline: float) -> str | None:
    tokens = _bedrock_bearer_tokens()
    if not tokens:
        return None
    region = _bedrock_region()
    endpoint = f"https://bedrock-runtime.{region}.amazonaws.com/model/{urllib_parse.quote(model_id, safe='')}/converse"
    body = {
        "system": [{"text": system}],
        "messages": [{"role": "user", "content": [{"text": user}]}],
        "inferenceConfig": {"temperature": 0.3, "maxTokens": 900},
    }

    for token in tokens:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        timeout = min(_request_timeout_seconds(), max(1.0, remaining))
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=timeout) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (urllib_error.URLError, TimeoutError, json.JSONDecodeError):
            continue
        except urllib_error.HTTPError:
            continue

        text = _extract_bedrock_text(parsed if isinstance(parsed, dict) else {})
        if text:
            return text
    return None


def generate_recovery_student_email_body(
    *,
    student_name: str,
    overall_attendance_percent: float,
    watch_threshold: float,
    subject_focus_lines: list[str],
    risk_level: str,
    consecutive_absences: int,
    missed_remedials: int,
    next_slot_line: str,
    office_hour_line: str,
) -> str | None:
    provider = _recovery_llm_provider()
    if provider != "bedrock":
        return None
    deadline = time.monotonic() + _total_timeout_seconds()
    model_id = _bedrock_model_id("STUDENT_EMAIL")
    system = (
        "You are Recovery Copilot for a university attendance platform. "
        "Write a concise, supportive but firm email to a student about attendance recovery. "
        "Do not mention internal systems, API keys, or configuration. Do not use markdown; plain text only."
    )
    user = "\n".join(
        [
            f"Student name: {student_name}",
            f"Risk level: {risk_level}",
            f"Overall attendance: {overall_attendance_percent:.1f}%",
            f"Safety threshold: {watch_threshold:.0f}%",
            "Subjects below threshold:",
            *subject_focus_lines,
            f"Consecutive absences: {consecutive_absences}",
            f"Missed remedials: {missed_remedials}",
            "Scheduling lines to include verbatim:",
            next_slot_line,
            office_hour_line,
            "",
            "Requirements:",
            "1) Start with a 1-line summary of the situation.",
            "2) Include a short subject-wise action plan (bullet points).",
            "3) Include precautionary measures and how to prevent future drops.",
            "4) Include resources: Saarthi (in-app mentor), campus remedial classes, and quick revision plan.",
            "5) End with: 'If you are facing a genuine issue, talk to Saarthi in the app immediately.'",
        ]
    )
    return _bedrock_converse_text(model_id=model_id, system=system, user=user, deadline=deadline)


def generate_recovery_faculty_email_body(
    *,
    faculty_name: str,
    student_name: str,
    course_code: str,
    course_attendance_percent: float,
    overall_attendance_percent: float,
    risk_level: str,
    consecutive_absences: int,
) -> str | None:
    provider = _recovery_llm_provider()
    if provider != "bedrock":
        return None
    deadline = time.monotonic() + _total_timeout_seconds()
    model_id = _bedrock_model_id("FACULTY_EMAIL")
    system = (
        "You are Recovery Copilot assisting faculty. "
        "Write a short, actionable intervention email to a faculty member. "
        "No markdown; plain text only."
    )
    user = "\n".join(
        [
            f"Faculty name: {faculty_name}",
            f"Student name: {student_name}",
            f"Course: {course_code}",
            f"Course attendance: {course_attendance_percent:.1f}%",
            f"Overall attendance: {overall_attendance_percent:.1f}%",
            f"Risk level: {risk_level}",
            f"Consecutive absences: {consecutive_absences}",
            "",
            "Requirements:",
            "1) Request remedial sessions and a quick checkpoint test plan.",
            "2) Ask for weekly tracking until >= threshold.",
            "3) Keep it under 1600 characters.",
        ]
    )
    text = _bedrock_converse_text(model_id=model_id, system=system, user=user, deadline=deadline)
    if text and len(text) > 1800:
        return text[:1800].rstrip() + "..."
    return text
