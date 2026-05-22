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
    if _recovery_openrouter_api_keys():
        return "openrouter"
    if _recovery_gemini_api_keys():
        return "gemini"
    if _recovery_nvidia_api_keys():
        return "nvidia"
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
    for name in ("RECOVERY_BEDROCK_API_KEY", "AWS_BEARER_TOKEN_BEDROCK", "COPILOT_BEDROCK_API_KEY"):
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


def _json_key_list(secret_name: str) -> list[str]:
    raw = str(resolve_secret(secret_name, default="") or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [str(item or "").strip() for item in parsed if str(item or "").strip()]
    if isinstance(parsed, str) and parsed.strip():
        return [parsed.strip()]
    return []


def _csv_key_list(secret_name: str) -> list[str]:
    raw = str(resolve_secret(secret_name, default="") or "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def _recovery_gemini_api_keys() -> list[str]:
    values: list[str] = []
    values.extend(_json_key_list("RECOVERY_GEMINI_API_KEYS_JSON"))
    values.extend(_csv_key_list("RECOVERY_GEMINI_API_KEYS"))
    single = str(resolve_secret("RECOVERY_GEMINI_API_KEY", default="") or "").strip()
    if single:
        values.append(single)
    if values:
        return _dedupe(values)
    values.extend(_json_key_list("COPILOT_GEMINI_API_KEYS_JSON"))
    values.extend(_csv_key_list("COPILOT_GEMINI_API_KEYS"))
    single = str(resolve_secret("COPILOT_GEMINI_API_KEY", default="") or "").strip()
    if single:
        values.append(single)
    return _dedupe(values)


def _recovery_openrouter_api_keys() -> list[str]:
    values: list[str] = []
    values.extend(_json_key_list("RECOVERY_OPENROUTER_API_KEYS_JSON"))
    values.extend(_csv_key_list("RECOVERY_OPENROUTER_API_KEYS"))
    single = str(resolve_secret("RECOVERY_OPENROUTER_API_KEY", default="") or "").strip()
    if single:
        values.append(single)
    if values:
        return _dedupe(values)
    values.extend(_json_key_list("COPILOT_OPENROUTER_API_KEYS_JSON"))
    values.extend(_csv_key_list("COPILOT_OPENROUTER_API_KEYS"))
    single = str(resolve_secret("COPILOT_OPENROUTER_API_KEY", default="") or "").strip()
    if single:
        values.append(single)
    return _dedupe(values)


def _recovery_nvidia_api_keys() -> list[str]:
    values: list[str] = []
    values.extend(_json_key_list("RECOVERY_NVIDIA_API_KEYS_JSON"))
    values.extend(_csv_key_list("RECOVERY_NVIDIA_API_KEYS"))
    single = str(resolve_secret("RECOVERY_NVIDIA_API_KEY", default="") or "").strip()
    if single:
        values.append(single)
    return _dedupe(values)


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


def _extract_gemini_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return ""
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        texts = [
            str(part.get("text") or "").strip()
            for part in parts
            if isinstance(part, dict) and str(part.get("text") or "").strip()
        ]
        if texts:
            return "\n".join(texts).strip()
    return ""


def _extract_openrouter_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list):
        return ""
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            texts = [
                str(item.get("text") or "").strip()
                for item in content
                if isinstance(item, dict) and str(item.get("text") or "").strip()
            ]
            if texts:
                return "\n".join(texts).strip()
    return ""


def _recovery_gemini_model() -> str:
    return (
        str(resolve_secret("RECOVERY_GEMINI_MODEL", default="") or "").strip()
        or str(resolve_secret("COPILOT_LLM_MODEL", default="") or "").strip()
        or "gemini-2.5-flash"
    )


def _recovery_openrouter_model() -> str:
    explicit = str(resolve_secret("RECOVERY_OPENROUTER_MODEL", default="") or "").strip()
    if explicit:
        return explicit
    copilot = str(resolve_secret("COPILOT_OPENROUTER_MODEL", default="") or "").strip()
    if copilot:
        return copilot
    model = _recovery_gemini_model()
    if "/" in model:
        return model
    if model.startswith("gemini-"):
        return f"google/{model}"
    return model or "google/gemini-2.5-flash"


def _recovery_gemini_base_url() -> str:
    return (
        str(resolve_secret("RECOVERY_GEMINI_API_BASE_URL", default="") or "").strip()
        or str(resolve_secret("COPILOT_GEMINI_API_BASE_URL", default="") or "").strip()
        or str(resolve_secret("GEMINI_API_BASE_URL", default="https://generativelanguage.googleapis.com/v1beta") or "").strip()
        or "https://generativelanguage.googleapis.com/v1beta"
    ).rstrip("/")


def _recovery_openrouter_base_url() -> str:
    return (
        str(resolve_secret("RECOVERY_OPENROUTER_API_BASE_URL", default="") or "").strip()
        or str(resolve_secret("COPILOT_OPENROUTER_API_BASE_URL", default="") or "").strip()
        or str(resolve_secret("OPENROUTER_API_BASE_URL", default="https://openrouter.ai/api/v1") or "").strip()
        or "https://openrouter.ai/api/v1"
    ).rstrip("/")


def _recovery_openrouter_site_url() -> str:
    return (
        str(resolve_secret("RECOVERY_OPENROUTER_SITE_URL", default="") or "").strip()
        or str(resolve_secret("COPILOT_OPENROUTER_SITE_URL", default="") or "").strip()
        or str(resolve_secret("OPENROUTER_SITE_URL", default="") or "").strip()
    )


def _recovery_openrouter_app_name() -> str:
    return (
        str(resolve_secret("RECOVERY_OPENROUTER_APP_NAME", default="") or "").strip()
        or str(resolve_secret("COPILOT_OPENROUTER_APP_NAME", default="") or "").strip()
        or "LPU Smart Campus Recovery Copilot"
    )


def _recovery_nvidia_base_url() -> str:
    return (
        str(resolve_secret("RECOVERY_NVIDIA_API_BASE_URL", default="") or "").strip()
        or "https://integrate.api.nvidia.com/v1"
    ).rstrip("/")


def _recovery_nvidia_model() -> str:
    return (
        str(resolve_secret("RECOVERY_NVIDIA_MODEL", default="") or "").strip()
        or "google/gemma-3n-e2b-it"
    )


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


def _nvidia_text(*, system: str, user: str, deadline: float) -> str | None:
    keys = _recovery_nvidia_api_keys()
    if not keys:
        return None
    body = {
        "model": _recovery_nvidia_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 900,
        "temperature": 0.2,
        "top_p": 0.7,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stream": False,
    }
    endpoint = f"{_recovery_nvidia_base_url()}/chat/completions"
    for api_key in keys:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=min(_request_timeout_seconds(), max(1.0, remaining))) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (urllib_error.HTTPError, urllib_error.URLError, TimeoutError, json.JSONDecodeError):
            continue
        text = _extract_openrouter_text(parsed if isinstance(parsed, dict) else {})
        if text:
            return text
    return None


def _gemini_text(*, system: str, user: str, deadline: float) -> str | None:
    keys = _recovery_gemini_api_keys()
    if not keys:
        return None
    endpoint = (
        f"{_recovery_gemini_base_url()}/models/"
        f"{urllib_parse.quote(_recovery_gemini_model(), safe='')}:generateContent"
    )
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.2, "topP": 0.9, "maxOutputTokens": 900},
    }
    for api_key in keys:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=min(_request_timeout_seconds(), max(1.0, remaining))) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (urllib_error.HTTPError, urllib_error.URLError, TimeoutError, json.JSONDecodeError):
            continue
        text = _extract_gemini_text(parsed if isinstance(parsed, dict) else {})
        if text:
            return text
    return None


def _openrouter_text(*, system: str, user: str, deadline: float) -> str | None:
    keys = _recovery_openrouter_api_keys()
    if not keys:
        return None
    body = {
        "model": _recovery_openrouter_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 900,
    }
    endpoint = f"{_recovery_openrouter_base_url()}/chat/completions"
    for api_key in keys:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        site_url = _recovery_openrouter_site_url()
        if site_url:
            headers["HTTP-Referer"] = site_url
        app_name = _recovery_openrouter_app_name()
        if app_name:
            headers["X-Title"] = app_name
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=min(_request_timeout_seconds(), max(1.0, remaining))) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (urllib_error.HTTPError, urllib_error.URLError, TimeoutError, json.JSONDecodeError):
            continue
        text = _extract_openrouter_text(parsed if isinstance(parsed, dict) else {})
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
    study_resource_lines: list[str] | None = None,
) -> str | None:
    provider = _recovery_llm_provider()
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
            "Subject-specific study links to include verbatim without adding unrelated subjects:",
            *(study_resource_lines or []),
            "",
            "Requirements:",
            "1) Start with a 1-line summary of the situation.",
            "2) Include a short subject-wise action plan (bullet points).",
            "3) Include precautionary measures and how to prevent future drops.",
            "4) Include the provided study links exactly under their matching subject only.",
            "5) Include resources: Saarthi (in-app mentor), campus remedial classes, and quick revision plan.",
            "6) End with: 'If you are facing a genuine issue, talk to Saarthi in the app immediately.'",
        ]
    )
    attempts: list[str]
    if provider == "bedrock":
        attempts = ["bedrock", "openrouter", "gemini", "nvidia"]
    elif provider == "gemini":
        attempts = ["gemini", "openrouter", "nvidia"]
    elif provider == "openrouter":
        attempts = ["openrouter", "gemini", "nvidia"]
    elif provider == "nvidia":
        attempts = ["nvidia"]
    else:
        attempts = []
    for item in attempts:
        if item == "bedrock":
            text = _bedrock_converse_text(model_id=model_id, system=system, user=user, deadline=deadline)
        elif item == "gemini":
            text = _gemini_text(system=system, user=user, deadline=deadline)
        elif item == "openrouter":
            text = _openrouter_text(system=system, user=user, deadline=deadline)
        elif item == "nvidia":
            text = _nvidia_text(system=system, user=user, deadline=deadline)
        else:
            text = None
        if text:
            return text
    return None


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
    attempts: list[str]
    if provider == "bedrock":
        attempts = ["bedrock", "openrouter", "gemini", "nvidia"]
    elif provider == "gemini":
        attempts = ["gemini", "openrouter", "nvidia"]
    elif provider == "openrouter":
        attempts = ["openrouter", "gemini", "nvidia"]
    elif provider == "nvidia":
        attempts = ["nvidia"]
    else:
        attempts = []
    text = None
    for item in attempts:
        if item == "bedrock":
            text = _bedrock_converse_text(model_id=model_id, system=system, user=user, deadline=deadline)
        elif item == "gemini":
            text = _gemini_text(system=system, user=user, deadline=deadline)
        elif item == "openrouter":
            text = _openrouter_text(system=system, user=user, deadline=deadline)
        elif item == "nvidia":
            text = _nvidia_text(system=system, user=user, deadline=deadline)
        if text:
            break
    if text and len(text) > 1800:
        return text[:1800].rstrip() + "..."
    return text
