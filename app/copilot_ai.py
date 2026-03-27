from __future__ import annotations

import json
import os
import re
import time
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .enterprise_controls import resolve_secret


def _dedup_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def _ordered_secret_pool(*, keyring_secret_name: str, active_secret_name: str) -> list[str]:
    ordered: list[str] = []
    keyring_raw = str(resolve_secret(keyring_secret_name, default="") or "").strip()
    active_key_id = str(resolve_secret(active_secret_name, default="") or "").strip()
    if not keyring_raw:
        return ordered
    try:
        parsed = json.loads(keyring_raw)
    except json.JSONDecodeError:
        return ordered

    if isinstance(parsed, dict):
        if active_key_id:
            active_value = str(parsed.get(active_key_id) or "").strip()
            if active_value:
                ordered.append(active_value)
        ordered.extend(str(value or "").strip() for value in parsed.values())
    elif isinstance(parsed, list):
        ordered.extend(str(value or "").strip() for value in parsed)
    elif isinstance(parsed, str):
        ordered.append(parsed.strip())

    return _dedup_preserve_order(ordered)


def _collect_indexed_keys(prefix: str) -> list[str]:
    indexed_keys: list[tuple[int, str]] = []
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        suffix = env_key.split(prefix, 1)[1]
        try:
            index = int(suffix)
        except ValueError:
            continue
        cleaned = str(env_value or "").strip()
        if cleaned:
            indexed_keys.append((index, cleaned))
    return [value for _, value in sorted(indexed_keys, key=lambda item: item[0])]


def _partition_shared_pool(values: list[str], *, pick_even_indexes: bool) -> list[str]:
    # Keep singleton shared pools usable so one-key deployments do not silently disable Copilot.
    if len(values) <= 1:
        return list(values)
    return [
        value
        for index, value in enumerate(values)
        if ((index % 2) == 0) == bool(pick_even_indexes)
    ]


def _shared_gemini_api_keys() -> list[str]:
    collected: list[str] = []
    collected.extend(
        _ordered_secret_pool(
            keyring_secret_name="GEMINI_API_KEYRING_JSON",
            active_secret_name="GEMINI_ACTIVE_KEY_ID",
        )
    )
    json_blob = str(resolve_secret("GEMINI_API_KEYS_JSON", default="") or "").strip()
    if json_blob:
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            collected.extend(str(item or "").strip() for item in parsed)
        elif isinstance(parsed, str):
            collected.append(parsed.strip())
    csv_blob = str(resolve_secret("GEMINI_API_KEYS", default="") or "").strip()
    if csv_blob:
        collected.extend(part.strip() for part in csv_blob.split(","))
    single_key = str(resolve_secret("GEMINI_API_KEY", default="") or "").strip()
    if single_key:
        collected.append(single_key)
    collected.extend(_collect_indexed_keys("GEMINI_API_KEY_"))
    return _dedup_preserve_order(collected)


def _copilot_dedicated_gemini_api_keys() -> list[str]:
    collected: list[str] = []
    collected.extend(
        _ordered_secret_pool(
            keyring_secret_name="COPILOT_GEMINI_API_KEYRING_JSON",
            active_secret_name="COPILOT_GEMINI_ACTIVE_KEY_ID",
        )
    )

    for secret_name in ("COPILOT_GEMINI_API_KEYS_JSON",):
        json_blob = str(resolve_secret(secret_name, default="") or "").strip()
        if not json_blob:
            continue
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            collected.extend(str(item or "").strip() for item in parsed)
        elif isinstance(parsed, str):
            collected.append(parsed.strip())

    for secret_name in ("COPILOT_GEMINI_API_KEYS",):
        csv_blob = str(resolve_secret(secret_name, default="") or "").strip()
        if csv_blob:
            collected.extend(part.strip() for part in csv_blob.split(","))

    for secret_name in ("COPILOT_GEMINI_API_KEY",):
        single_key = str(resolve_secret(secret_name, default="") or "").strip()
        if single_key:
            collected.append(single_key)

    collected.extend(_collect_indexed_keys("COPILOT_GEMINI_API_KEY_"))
    return _dedup_preserve_order(collected)


def _copilot_gemini_api_keys() -> list[str]:
    dedicated = _copilot_dedicated_gemini_api_keys()
    if dedicated:
        return dedicated
    shared = _shared_gemini_api_keys()
    return _dedup_preserve_order(_partition_shared_pool(shared, pick_even_indexes=False))


def _shared_openrouter_api_keys() -> list[str]:
    collected: list[str] = []
    collected.extend(
        _ordered_secret_pool(
            keyring_secret_name="OPENROUTER_API_KEYRING_JSON",
            active_secret_name="OPENROUTER_ACTIVE_KEY_ID",
        )
    )
    json_blob = str(resolve_secret("OPENROUTER_API_KEYS_JSON", default="") or "").strip()
    if json_blob:
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            collected.extend(str(item or "").strip() for item in parsed)
        elif isinstance(parsed, str):
            collected.append(parsed.strip())
    csv_blob = str(resolve_secret("OPENROUTER_API_KEYS", default="") or "").strip()
    if csv_blob:
        collected.extend(part.strip() for part in csv_blob.split(","))
    single_key = str(resolve_secret("OPENROUTER_API_KEY", default="") or "").strip()
    if single_key:
        collected.append(single_key)
    return _dedup_preserve_order(collected)


def _copilot_dedicated_openrouter_api_keys() -> list[str]:
    collected: list[str] = []
    collected.extend(
        _ordered_secret_pool(
            keyring_secret_name="COPILOT_OPENROUTER_API_KEYRING_JSON",
            active_secret_name="COPILOT_OPENROUTER_ACTIVE_KEY_ID",
        )
    )
    for secret_name in ("COPILOT_OPENROUTER_API_KEYS_JSON",):
        json_blob = str(resolve_secret(secret_name, default="") or "").strip()
        if not json_blob:
            continue
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            collected.extend(str(item or "").strip() for item in parsed)
        elif isinstance(parsed, str):
            collected.append(parsed.strip())

    for secret_name in ("COPILOT_OPENROUTER_API_KEYS",):
        csv_blob = str(resolve_secret(secret_name, default="") or "").strip()
        if csv_blob:
            collected.extend(part.strip() for part in csv_blob.split(","))

    for secret_name in ("COPILOT_OPENROUTER_API_KEY",):
        single_key = str(resolve_secret(secret_name, default="") or "").strip()
        if single_key:
            collected.append(single_key)

    return _dedup_preserve_order(collected)


def _copilot_openrouter_api_keys() -> list[str]:
    dedicated = _copilot_dedicated_openrouter_api_keys()
    if dedicated:
        return dedicated
    shared = _shared_openrouter_api_keys()
    return _dedup_preserve_order(_partition_shared_pool(shared, pick_even_indexes=False))


def _copilot_llm_enabled() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    raw = (os.getenv("COPILOT_LLM_ENABLED", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _copilot_llm_provider() -> str:
    explicit = str(os.getenv("COPILOT_LLM_PROVIDER") or "").strip().lower()
    if explicit:
        return explicit
    if _copilot_gemini_api_keys():
        return "gemini"
    if _copilot_openrouter_api_keys():
        return "openrouter"
    return ""


def _copilot_llm_model() -> str:
    return str(os.getenv("COPILOT_LLM_MODEL") or "gemini-2.5-flash").strip() or "gemini-2.5-flash"


def _copilot_openrouter_model() -> str:
    explicit = str(os.getenv("COPILOT_OPENROUTER_MODEL") or "").strip()
    if explicit:
        return explicit
    base = _copilot_llm_model().strip()
    if not base:
        return "google/gemini-2.5-flash"
    if "/" in base:
        return base
    if base.lower().startswith("gemini-"):
        return f"google/{base}"
    return base


def _copilot_gemini_base_url() -> str:
    raw = str(
        resolve_secret("COPILOT_GEMINI_API_BASE_URL", default="")
        or resolve_secret("GEMINI_API_BASE_URL", default="https://generativelanguage.googleapis.com/v1beta")
        or "https://generativelanguage.googleapis.com/v1beta"
    ).strip()
    return raw.rstrip("/")


def _copilot_openrouter_base_url() -> str:
    raw = str(
        resolve_secret("COPILOT_OPENROUTER_API_BASE_URL", default="")
        or resolve_secret("OPENROUTER_API_BASE_URL", default="https://openrouter.ai/api/v1")
        or "https://openrouter.ai/api/v1"
    ).strip()
    return raw.rstrip("/")


def _copilot_openrouter_site_url() -> str:
    return str(
        resolve_secret("COPILOT_OPENROUTER_SITE_URL", default="")
        or resolve_secret("OPENROUTER_SITE_URL", default="")
        or ""
    ).strip()


def _copilot_openrouter_app_name() -> str:
    return str(
        resolve_secret("COPILOT_OPENROUTER_APP_NAME", default="")
        or resolve_secret("OPENROUTER_APP_NAME", default="LPU Smart Campus Copilot")
        or "LPU Smart Campus Copilot"
    ).strip()


def _float_env(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        value = float(raw)
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _copilot_request_timeout_seconds() -> float:
    return _float_env("COPILOT_LLM_REQUEST_TIMEOUT_SECONDS", 4.0, minimum=1.0, maximum=12.0)


def _copilot_total_timeout_seconds() -> float:
    return _float_env("COPILOT_LLM_TOTAL_TIMEOUT_SECONDS", 10.0, minimum=2.0, maximum=20.0)


def _copilot_temperature() -> float:
    return _float_env("COPILOT_LLM_TEMPERATURE", 0.2, minimum=0.0, maximum=1.0)


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
            cleaned = content.strip()
            if cleaned:
                return cleaned
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if str(item.get("type") or "").strip() not in {"", "text"}:
                    continue
                text = str(item.get("text") or "").strip()
                if text:
                    parts.append(text)
            if parts:
                return "\n".join(parts).strip()
    return ""


def _error_detail(exc: urllib_error.HTTPError) -> str:
    try:
        detail = exc.read().decode("utf-8", errors="ignore")
    except Exception:
        detail = ""
    return detail or str(exc)


def _is_key_rotation_error(status_code: int, detail: str) -> bool:
    normalized = " ".join(str(detail or "").lower().split())
    if status_code == 429:
        return True
    if status_code not in {400, 401, 402, 403}:
        return False
    markers = (
        "quota",
        "rate limit",
        "resource_exhausted",
        "invalid api key",
        "api key not valid",
        "insufficient",
        "credit",
        "billing",
        "expired",
        "revoked",
    )
    return any(marker in normalized for marker in markers)


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    cleaned = str(raw_text or "").strip()
    if not cleaned:
        return None
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace < 0 or last_brace <= first_brace:
        return None
    snippet = cleaned[first_brace : last_brace + 1]
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_lines(value: Any, *, minimum: int, maximum: int) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = " ".join(str(item or "").split()).strip()
        if not text:
            continue
        if text.lower().startswith("as an ai"):
            continue
        if re.search(r"https?://", text, flags=re.IGNORECASE):
            continue
        out.append(text[:220])
        if len(out) >= maximum:
            break
    if len(out) < minimum:
        return []
    return out


def _normalize_title(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    return text[:90]


def _copilot_is_broad_query(query_text: str) -> bool:
    normalized = re.sub(r"\s+", " ", str(query_text or "").strip().lower())
    if not normalized:
        return False
    markers = (
        "summary",
        "summarize",
        "overview",
        "overall",
        "across modules",
        "across all modules",
        "all modules",
        "module-wise",
        "module wise",
        "dashboard",
    )
    return any(marker in normalized for marker in markers)


def _build_prompt(
    *,
    query_text: str,
    role: str,
    module_labels: list[str],
    denied_labels: list[str],
    explanation: list[str],
    evidence: list[dict[str, str]],
    next_steps: list[str],
    entities: dict[str, Any],
) -> tuple[str, str]:
    broad_scope = _copilot_is_broad_query(query_text)
    explanation_limit = 4 if broad_scope else 3
    next_steps_limit = 3 if broad_scope else 2
    active_module = str((entities or {}).get("active_module") or "").strip()
    active_module_context = entities.get("active_module_context") if isinstance(entities, dict) else {}
    ui_context = entities.get("ui_context") if isinstance(entities, dict) else {}
    system = (
        "You are Campus Copilot for the LPU Smart Campus app. "
        "Answer strictly using only the provided app context. "
        "Treat the active module as the user's current screen unless the user explicitly asks for a broad summary. "
        "Answer only what the user asked, and skip unrelated module details. "
        "Do not provide external or generic life advice. "
        "Never suggest external websites, email, phone, browser troubleshooting, or non-app workflows unless the provided app context explicitly says that is the only resolution. "
        "Never reveal secrets, credentials, API keys, tokens, passwords, cookies, environment variables, connection strings, or internal configuration values. "
        "If the user asks for protected values or secret locations, refuse briefly and redirect to safe in-app help. "
        "Never ask for extra identifiers if the current screen context already includes the selected student, class, slot, thread, or record. "
        "If data is missing, state that it is unavailable in app context and give in-app resolution steps only. "
        "Return strict JSON only with keys: title, explanation, next_steps. "
        "Rules: explanation must be concise and focused on resolving the user's issue in-app; "
        f"explanation must be 1-{explanation_limit} short points; "
        f"next_steps must be 0-{next_steps_limit} concrete in-app actions. "
        "If the query is about one issue, keep the answer single-issue. "
        "Prefer exact blockers, selected records, and current module controls over generic summaries. "
        "Only provide cross-module coverage when the user explicitly asks for a summary or overview."
    )
    context_payload = {
        "query": str(query_text or "").strip(),
        "role": str(role or "").strip().lower(),
        "active_module": active_module or None,
        "modules_answered": [str(item) for item in module_labels if str(item or "").strip()],
        "modules_denied": [str(item) for item in denied_labels if str(item or "").strip()],
        "app_context_explanation": [str(item) for item in explanation if str(item or "").strip()],
        "app_context_evidence": [
            {
                "label": str(item.get("label") or "").strip(),
                "value": str(item.get("value") or "").strip(),
                "status": str(item.get("status") or "").strip().lower(),
            }
            for item in evidence
            if isinstance(item, dict)
        ],
        "default_next_steps": [str(item) for item in next_steps if str(item or "").strip()],
        "active_module_context": active_module_context if isinstance(active_module_context, dict) else {},
        "ui_context": ui_context if isinstance(ui_context, dict) else {},
        "entities": entities if isinstance(entities, dict) else {},
        "response_contract": {
            "broad_scope": broad_scope,
            "max_explanation_points": explanation_limit,
            "max_next_steps": next_steps_limit,
        },
    }
    user = (
        "User request and app facts:\n"
        + json.dumps(context_payload, ensure_ascii=True, separators=(",", ":"))
        + "\nReturn JSON only."
    )
    return system, user


def _try_gemini_json(
    *,
    system_prompt: str,
    user_prompt: str,
    deadline: float,
) -> dict[str, Any] | None:
    keys = _copilot_gemini_api_keys()
    if not keys:
        return None
    model = _copilot_llm_model()
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": _copilot_temperature(),
            "topP": 0.9,
            "maxOutputTokens": 320,
        },
    }
    base_url = _copilot_gemini_base_url()
    endpoint = f"{base_url}/models/{urllib_parse.quote(model, safe='')}:generateContent"

    for api_key in keys:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        timeout = min(_copilot_request_timeout_seconds(), max(1.0, remaining))
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=timeout) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            detail = _error_detail(exc)
            if _is_key_rotation_error(exc.code, detail):
                continue
            return None
        except (urllib_error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        text = _extract_gemini_text(parsed)
        result = _extract_json_object(text)
        if result:
            return result
    return None


def _try_openrouter_json(
    *,
    system_prompt: str,
    user_prompt: str,
    deadline: float,
) -> dict[str, Any] | None:
    keys = _copilot_openrouter_api_keys()
    if not keys:
        return None

    body = {
        "model": _copilot_openrouter_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": _copilot_temperature(),
        "top_p": 0.9,
        "max_tokens": 320,
    }
    endpoint = f"{_copilot_openrouter_base_url()}/chat/completions"
    site_url = _copilot_openrouter_site_url()
    app_name = _copilot_openrouter_app_name()

    for api_key in keys:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        timeout = min(_copilot_request_timeout_seconds(), max(1.0, remaining))
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        if site_url:
            headers["HTTP-Referer"] = site_url
        if app_name:
            headers["X-Title"] = app_name
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=timeout) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            detail = _error_detail(exc)
            if _is_key_rotation_error(exc.code, detail):
                continue
            return None
        except (urllib_error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        text = _extract_openrouter_text(parsed)
        result = _extract_json_object(text)
        if result:
            return result
    return None


def generate_structured_copilot_answer(
    *,
    query_text: str,
    role: str,
    module_labels: list[str],
    denied_labels: list[str],
    explanation: list[str],
    evidence: list[dict[str, str]],
    next_steps: list[str],
    entities: dict[str, Any],
) -> dict[str, Any] | None:
    if not _copilot_llm_enabled():
        return None
    provider = _copilot_llm_provider()
    if not provider:
        return None

    system_prompt, user_prompt = _build_prompt(
        query_text=query_text,
        role=role,
        module_labels=module_labels,
        denied_labels=denied_labels,
        explanation=explanation,
        evidence=evidence,
        next_steps=next_steps,
        entities=entities,
    )
    deadline = time.monotonic() + _copilot_total_timeout_seconds()

    parsed: dict[str, Any] | None = None
    if provider == "gemini":
        parsed = _try_gemini_json(system_prompt=system_prompt, user_prompt=user_prompt, deadline=deadline)
        if parsed is None:
            parsed = _try_openrouter_json(system_prompt=system_prompt, user_prompt=user_prompt, deadline=deadline)
    elif provider == "openrouter":
        parsed = _try_openrouter_json(system_prompt=system_prompt, user_prompt=user_prompt, deadline=deadline)
        if parsed is None:
            parsed = _try_gemini_json(system_prompt=system_prompt, user_prompt=user_prompt, deadline=deadline)
    else:
        return None

    if not isinstance(parsed, dict):
        return None
    broad_scope = _copilot_is_broad_query(query_text)
    normalized = {
        "title": _normalize_title(parsed.get("title")),
        "explanation": _normalize_lines(
            parsed.get("explanation"),
            minimum=1,
            maximum=4 if broad_scope else 3,
        ),
        "next_steps": _normalize_lines(
            parsed.get("next_steps"),
            minimum=0,
            maximum=3 if broad_scope else 2,
        ),
    }
    if not normalized["explanation"]:
        return None
    return normalized
