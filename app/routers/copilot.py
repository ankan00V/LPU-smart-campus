from __future__ import annotations

import json
import logging
import math
import os
import re
from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import CurrentUser, require_roles, sync_auth_user_pk_sequence
from ..copilot_ai import generate_structured_copilot_answer
from ..database import get_db
from ..mongo import mirror_document, mirror_event
from .attendance import (
    _resolve_student_schedule_context,
    _window_flags,
    get_student_attendance_aggregate,
)
from .messages import _ensure_student_rms_cases
from .remedial import (
    _faculty_allowed_sections as remedial_faculty_allowed_sections,
    _normalize_sections,
    create_makeup_class,
    send_remedial_code_to_sections,
)

router = APIRouter(prefix="/copilot", tags=["Explainable Campus Copilot"])
logger = logging.getLogger(__name__)

REGISTRATION_PATTERN = re.compile(r"^[A-Z0-9/-]+$")
SCHEDULE_ID_RE = re.compile(r"\bschedule(?:\s*id)?\s*#?\s*(\d+)\b", re.IGNORECASE)
STUDENT_ID_RE = re.compile(r"\bstudent(?:\s*id)?\s*#?\s*(\d+)\b", re.IGNORECASE)
COURSE_ID_RE = re.compile(r"\bcourse\s*id\s*#?\s*(\d+)\b", re.IGNORECASE)
COURSE_CODE_RE = re.compile(r"\bcourse(?:\s*code)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]{1,19})\b", re.IGNORECASE)
SECTION_RE = re.compile(r"\bsection\s+([A-Z0-9/_-]{1,80})\b", re.IGNORECASE)
ROOM_RE = re.compile(r"\broom\s+([A-Z0-9][A-Z0-9\s/_-]{0,79})\b", re.IGNORECASE)
REGISTRATION_RE = re.compile(
    r"\b(?:registration(?:\s*number)?|reg(?:istration)?(?:\s*(?:number|no))?)\s*[:#-]?\s*([A-Z0-9/-]{3,40})\b",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
SENSITIVE_DISCLOSURE_MARKERS = (
    "show me",
    "show",
    "reveal",
    "give me",
    "give us",
    "give the",
    "tell me",
    "provide",
    "print",
    "dump",
    "list",
    "display",
    "expose",
    "share",
    "send me",
    "copy",
    "read out",
    "what is the",
    "what's the",
    "where is the",
    "where are the",
    "which is the",
    "fetch",
)
SENSITIVE_LOCATION_MARKERS = (
    "where is",
    "where are",
    "stored",
    "kept",
    "saved",
    "located",
    "location of",
)
SENSITIVE_SUBJECT_MARKERS = (
    "api key",
    "apikey",
    "secret",
    "secrets",
    "credential",
    "credentials",
    "token",
    "access token",
    "refresh token",
    "jwt",
    "bearer token",
    "session cookie",
    "cookie",
    "password",
    "passcode",
    "private key",
    "signing key",
    "encryption key",
    "webhook secret",
    "client secret",
    "connection string",
    "database url",
    "database uri",
    "db url",
    "db uri",
    "mongo uri",
    "mongodb uri",
    "postgres url",
    "postgres uri",
    ".env",
    "env file",
    "environment variable",
    "environment variables",
    "env var",
    "env vars",
    "otp code",
    "backup code",
    "mfa seed",
)
SENSITIVE_RAW_VALUE_MARKERS = (
    "actual",
    "current",
    "raw",
    "full",
    "exact",
    "real",
    "plaintext",
    "unmasked",
)
SENSITIVE_SAFE_CONTEXT_MARKERS = (
    "status",
    "rotation",
    "rotate",
    "rotated",
    "expiry",
    "expiration",
    "expired",
    "revoked",
    "revoke",
    "regenerate",
    "reset",
    "change",
    "update",
    "configured",
    "configuration",
    "health",
    "invalid",
    "failing",
    "blocked",
    "mask",
    "masked",
)


def _safe_json_dump(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"), ensure_ascii=True)


def _safe_json_load_list(raw_value: str | None) -> list[dict[str, Any]]:
    raw = str(raw_value or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _safe_json_load_dict(raw_value: str | None) -> dict[str, Any]:
    raw = str(raw_value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _supported_queries_for_role(role: models.UserRole) -> list[str]:
    if role == models.UserRole.STUDENT:
        return [
            "Why can't I mark attendance?",
            "Attendance isn't getting marked.",
            "What do I need to fix before I lose eligibility?",
            "Summarize my pending work across attendance, food, Saarthi, and remedial.",
        ]
    if role in {models.UserRole.ADMIN, models.UserRole.FACULTY}:
        return [
            "Create a remedial plan for course CSE501 section P132 on 2026-03-10 at 15:00",
            "Show why student 22BCS777 is flagged",
            "Give me a module-wise workload summary for today's accessible modules.",
        ]
    if role == models.UserRole.OWNER:
        return [
            "Summarize active food orders and delivery flow for my food shops.",
        ]
    return []


def _unsupported_response(current_user: CurrentUser) -> schemas.CopilotQueryResponse:
    supported = _supported_queries_for_role(current_user.role)
    explanation = ["This copilot accepts only audited campus actions and explainable institutional checks."]
    if supported:
        explanation.append("Use one of the supported prompt patterns for your role.")
    else:
        explanation.append("No academic copilot actions are available for your role.")
    return schemas.CopilotQueryResponse(
        intent=schemas.CopilotIntent.UNSUPPORTED,
        outcome=schemas.CopilotOutcome.BLOCKED,
        title="Copilot Request Not Supported",
        explanation=explanation,
        next_steps=supported,
    )


def _looks_like_sensitive_data_request(query_text: str) -> bool:
    normalized = re.sub(r"\s+", " ", str(query_text or "").strip().lower())
    if not normalized:
        return False
    if not any(marker in normalized for marker in SENSITIVE_SUBJECT_MARKERS):
        return False
    if any(marker in normalized for marker in SENSITIVE_SAFE_CONTEXT_MARKERS) and not any(
        marker in normalized for marker in SENSITIVE_RAW_VALUE_MARKERS
    ):
        return False
    return any(marker in normalized for marker in SENSITIVE_DISCLOSURE_MARKERS) or any(
        marker in normalized for marker in SENSITIVE_LOCATION_MARKERS
    ) or any(marker in normalized for marker in SENSITIVE_RAW_VALUE_MARKERS)


def _sensitive_request_denied_response(current_user: CurrentUser) -> schemas.CopilotQueryResponse:
    accessible_modules = _accessible_modules_for_role(current_user.role)
    module_labels = ", ".join(_copilot_module_label(module) for module in accessible_modules) or "your accessible modules"
    return schemas.CopilotQueryResponse(
        intent=schemas.CopilotIntent.MODULE_ASSIST,
        outcome=schemas.CopilotOutcome.DENIED,
        title="Sensitive Data Request Denied",
        explanation=[
            "Campus Copilot will not reveal secrets, credentials, tokens, API keys, environment values, or internal security material.",
            "It only answers with safe in-app context and approved workflow guidance.",
        ],
        actions=[_action("sensitive_data_guardrail", "denied", "Secret disclosure request blocked")],
        next_steps=[
            f"Ask about module status, blockers, or available actions inside {module_labels}.",
            "Ask why a workflow is blocked, and Campus Copilot will explain the in-app cause without exposing protected values.",
        ],
        entities={"guardrail": "sensitive_data_redaction", "accessible_modules": accessible_modules},
    )


COPILOT_MODULE_LABELS: dict[str, str] = {
    "attendance": "Attendance",
    "food": "Food Hall",
    "saarthi": "Saarthi",
    "remedial": "Remedial",
    "rms": "RMS",
    "administrative": "Administrative",
}

COPILOT_MODULE_QUERY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "attendance": (
        "attendance",
        "class",
        "classes",
        "timetable",
        "schedule",
        "eligibility",
        "absent",
        "present",
    ),
    "food": (
        "food",
        "order",
        "orders",
        "canteen",
        "cafeteria",
        "meal",
        "delivery",
        "shop",
        "kiosk",
        "payment",
    ),
    "saarthi": (
        "saarthi",
        "counselling",
        "counseling",
        "con111",
        "sunday session",
        "mentor",
    ),
    "remedial": (
        "remedial",
        "makeup",
        "make-up",
        "recovery class",
        "recovery",
    ),
    "rms": (
        "rms",
        "support case",
        "support ticket",
        "rectification",
        "correction",
        "escalation",
        "flagged",
        "flag",
    ),
    "administrative": (
        "administrative",
        "admin",
        "audit",
        "governance",
        "identity",
        "verification",
        "policy",
    ),
}


def _copilot_module_label(module_key: str) -> str:
    return COPILOT_MODULE_LABELS.get(str(module_key or "").strip().lower(), str(module_key or "").strip().title() or "Unknown")


def _accessible_modules_for_role(role: models.UserRole) -> list[str]:
    if role == models.UserRole.STUDENT:
        return ["attendance", "food", "saarthi", "remedial"]
    if role == models.UserRole.FACULTY:
        return ["attendance", "food", "rms", "remedial"]
    if role == models.UserRole.ADMIN:
        return ["attendance", "rms", "administrative"]
    if role == models.UserRole.OWNER:
        return ["food"]
    return []


def _mentioned_modules_from_query(query_text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", str(query_text or "").strip().lower())
    if not normalized:
        return []
    mentioned: list[str] = []
    for module_key, keywords in COPILOT_MODULE_QUERY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            mentioned.append(module_key)
    return mentioned


def _is_broad_module_summary_query(query_text: str) -> bool:
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


def _normalize_module_key(value: str | None) -> str | None:
    normalized = re.sub(r"\s+", "", str(value or "").strip().lower())
    if normalized in COPILOT_MODULE_LABELS:
        return normalized
    return None


def _context_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _context_str(value: Any) -> str:
    return str(value or "").strip()


def _context_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _context_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _context_date(value: Any) -> date | None:
    raw = _context_str(value)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _context_time(value: Any) -> time | None:
    raw = _context_str(value)
    if not raw:
        return None
    try:
        return time.fromisoformat(raw if len(raw) > 5 else f"{raw}:00")
    except ValueError:
        return None


def _append_unique(items: list[str], value: str | None) -> None:
    normalized = str(value or "").strip()
    if normalized and normalized not in items:
        items.append(normalized)


def _food_context(payload: schemas.CopilotQueryRequest) -> dict[str, Any]:
    root = _context_dict(payload.client_context)
    return _context_dict(root.get("food"))


def _focused_module_assist_next_steps(
    module_key: str,
    *,
    role: models.UserRole,
) -> list[str]:
    if module_key == "attendance":
        if role == models.UserRole.STUDENT:
            return [
                "Use Attendance on this screen to inspect the selected class or attendance details, then retry the in-app action there.",
                "If the issue is tied to one class, use the Attendance controls here instead of starting a new external flow.",
            ]
        if role == models.UserRole.FACULTY:
            return [
                "Use the Attendance schedule and rectification controls on this screen to review the affected class.",
                "Apply the next in-app attendance, rectification, or recovery action directly from Attendance.",
            ]
        return [
            "Use the Attendance admin controls on this screen to review schedules, overrides, or student updates.",
            "Retry the exact in-app Attendance action after correcting the flagged item.",
        ]
    if module_key == "food":
        if role == models.UserRole.STUDENT:
            return [
                "Use Food Hall on this screen: select a slot, add items from one shop, review the cart, then complete payment.",
                "Retry only the Food Hall step that is flagged in the explanation or evidence above.",
            ]
        return [
            "Use the Food Hall controls on this screen to review shops, orders, or slot setup.",
            "Retry the flagged Food Hall action after fixing the item shown above.",
        ]
    if module_key == "saarthi":
        return [
            "Use Saarthi on this screen to continue the weekly session or start the next required chat step.",
            "Retry the Saarthi action from this module after resolving the issue shown above.",
        ]
    if module_key == "remedial":
        if role == models.UserRole.FACULTY:
            return [
                "Use Remedial on this screen to review the selected class and schedule or resend the in-app remedial plan.",
                "Retry the remedial action from this module once the flagged item is corrected.",
            ]
        return [
            "Use Remedial on this screen to open the next class, message, or code tied to your current issue.",
            "Retry the same in-app remedial step after correcting the issue shown above.",
        ]
    if module_key == "rms":
        return [
            "Use RMS on this screen to review the selected student, thread, or attendance action already loaded in context.",
            "Apply the pending RMS workflow or attendance action directly from this module.",
        ]
    if module_key == "administrative":
        return [
            "Use the Administrative module on this screen to review the live cards, recovery queue, identity cases, or audit timeline.",
            "Retry the exact administrative action from this module after fixing the flagged item above.",
        ]
    return ["Retry the same action from the current module using the on-screen controls only."]


def _looks_like_food_order_blocker_query(query_text: str, *, active_module: str | None = None) -> bool:
    normalized = re.sub(r"\s+", " ", str(query_text or "").strip().lower().replace("’", "'"))
    if not normalized:
        return False
    explicit_phrases = (
        "why can't i order food",
        "why cant i order food",
        "cannot order food",
        "can't order food",
        "cant order food",
        "unable to order food",
        "food order not working",
        "food ordering not working",
        "food checkout blocked",
        "can't checkout",
        "cant checkout",
        "cannot checkout",
        "unable to checkout",
        "checkout blocked",
    )
    if any(phrase in normalized for phrase in explicit_phrases):
        return True

    blocker_markers = (
        "can't",
        "cant",
        "cannot",
        "unable",
        "won't",
        "wont",
        "blocked",
        "not working",
        "failed",
        "failing",
        "issue",
        "problem",
        "error",
        "stuck",
        "closed",
    )
    flow_markers = (
        "order",
        "checkout",
        "cart",
        "pay",
        "payment",
        "delivery",
    )
    in_food_scope = active_module == "food" or any(
        keyword in normalized for keyword in COPILOT_MODULE_QUERY_KEYWORDS["food"]
    )
    return in_food_scope and any(marker in normalized for marker in blocker_markers) and any(
        marker in normalized for marker in flow_markers
    )


def _student_food_order_blocker_assessment(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
    active_food_statuses: set[str],
    today: date,
) -> dict[str, Any]:
    explanation: list[str] = []
    evidence: list[schemas.CopilotEvidenceItem] = []
    next_steps: list[str] = []

    if not current_user.student_id:
        explanation.append("Student account is not linked correctly for Food Hall ordering.")
        evidence.append(_evidence("Account linkage", "Student account link missing", "fail"))
        return {
            "blocked": True,
            "title": "Food Ordering Blocked",
            "explanation": explanation,
            "evidence": evidence,
            "next_steps": [
                "Log in with the linked student account before retrying Food Hall checkout.",
            ],
            "entities": {
                "food": {
                    "ordering_blocked": True,
                    "student_linked": False,
                }
            },
            "action": _action("food_order_blocker_check", "blocked", explanation[0]),
        }

    food_context = _food_context(payload)
    slot_context = _context_dict(food_context.get("slot"))
    cart_context = _context_dict(food_context.get("cart"))
    checkout_context = _context_dict(food_context.get("checkout"))
    location_context = _context_dict(food_context.get("location"))
    order_gate_context = _context_dict(food_context.get("order_gate"))

    student_id = int(current_user.student_id)
    demo_enabled = _context_bool(food_context.get("demo_enabled")) is True
    order_date = _context_date(food_context.get("order_date")) or today
    selected_slot_id = _context_int(slot_context.get("slot_id"))
    selected_slot = db.get(models.BreakSlot, selected_slot_id) if selected_slot_id else None
    selected_slot_label = _context_str(slot_context.get("label")) or (selected_slot.label if selected_slot else "")
    selected_slot_start = _context_time(slot_context.get("start_time")) or (selected_slot.start_time if selected_slot else None)
    selected_slot_end = _context_time(slot_context.get("end_time")) or (selected_slot.end_time if selected_slot else None)
    slot_signal_present = bool(slot_context) and ("selected" in slot_context or "slot_id" in slot_context)
    selected_flag = _context_bool(slot_context.get("selected"))
    has_selected_slot = bool(selected_slot_id or selected_slot or selected_flag)

    cart_signal_present = bool(cart_context)
    cart_item_count = _context_int(cart_context.get("item_count"))
    cart_total_quantity = _context_int(cart_context.get("total_quantity"))
    cart_shop_id = _context_int(cart_context.get("shop_id"))
    cart_shop_name = _context_str(cart_context.get("shop_name"))
    if cart_item_count is None and cart_total_quantity is not None:
        cart_item_count = cart_total_quantity
    has_cart_items = bool((cart_item_count or 0) > 0 or (cart_total_quantity or 0) > 0)

    checkout_signal_present = bool(checkout_context)
    review_open = _context_bool(checkout_context.get("review_open")) is True
    delivery_point_selected = _context_bool(checkout_context.get("delivery_point_selected")) is True
    delivery_point = _context_str(checkout_context.get("delivery_point"))
    if delivery_point and not delivery_point_selected:
        delivery_point_selected = True

    location_signal_present = bool(location_context)
    location_verified = _context_bool(location_context.get("verified"))
    location_allowed = _context_bool(location_context.get("allowed"))
    location_fresh = _context_bool(location_context.get("fresh"))
    location_checking = _context_bool(location_context.get("checking")) is True
    location_message = _context_str(location_context.get("message"))

    order_gate_reason = _context_str(order_gate_context.get("reason")).lower()
    order_gate_message = _context_str(order_gate_context.get("message"))
    gate_can_order_now = _context_bool(order_gate_context.get("can_order_now"))
    gate_service_open_now = _context_bool(order_gate_context.get("service_open_now"))
    gate_date_allowed = _context_bool(order_gate_context.get("date_allowed"))
    gate_slot_elapsed = _context_bool(order_gate_context.get("slot_elapsed"))

    active_shop_count = int(
        db.query(func.count(models.FoodShop.id))
        .filter(models.FoodShop.is_active.is_(True))
        .scalar()
        or 0
    )
    active_orders_today = (
        db.query(models.FoodOrder)
        .filter(
            models.FoodOrder.student_id == student_id,
            models.FoodOrder.order_date == today,
            models.FoodOrder.status.in_([models.FoodOrderStatus(value) for value in active_food_statuses]),
        )
        .order_by(models.FoodOrder.created_at.desc(), models.FoodOrder.id.desc())
        .all()
    )
    latest_active_order = active_orders_today[0] if active_orders_today else None
    latest_order = (
        db.query(models.FoodOrder)
        .filter(models.FoodOrder.student_id == student_id)
        .order_by(models.FoodOrder.created_at.desc(), models.FoodOrder.id.desc())
        .first()
    )
    latest_active_shop_names = sorted({str(row.shop_name or "").strip() for row in active_orders_today if str(row.shop_name or "").strip()})

    single_shop_conflict = bool(
        cart_shop_id
        and any(row.shop_id and int(row.shop_id) != int(cart_shop_id) for row in active_orders_today)
    )
    slot_full = False
    slot_load_label = ""
    if selected_slot is not None:
        active_slot_orders = int(
            db.query(func.count(models.FoodOrder.id))
            .filter(
                models.FoodOrder.slot_id == int(selected_slot.id),
                models.FoodOrder.order_date == order_date,
                models.FoodOrder.status.notin_(
                    [
                        models.FoodOrderStatus.CANCELLED,
                        models.FoodOrderStatus.REJECTED,
                        models.FoodOrderStatus.REFUNDED,
                    ]
                ),
            )
            .scalar()
            or 0
        )
        slot_full = active_slot_orders >= int(selected_slot.max_orders)
        slot_load_label = f"{active_slot_orders}/{int(selected_slot.max_orders)} active orders"

    now_local = datetime.now()
    current_time = now_local.time()
    service_start = time(10, 0)
    service_end = time(21, 0)
    fallback_date_allowed = order_date == today
    fallback_service_open = service_start <= current_time < service_end
    fallback_slot_elapsed = bool(selected_slot_end and order_date == today and selected_slot_end <= current_time)

    if gate_date_allowed is None:
        gate_date_allowed = fallback_date_allowed
    if gate_service_open_now is None:
        gate_service_open_now = fallback_service_open
    if gate_slot_elapsed is None:
        gate_slot_elapsed = fallback_slot_elapsed
    if gate_can_order_now is None:
        gate_can_order_now = bool(gate_date_allowed and gate_service_open_now and not gate_slot_elapsed)
    if not order_gate_reason:
        if demo_enabled:
            order_gate_reason = "demo_bypass"
        elif not gate_date_allowed:
            order_gate_reason = "date_mismatch"
        elif not gate_service_open_now:
            order_gate_reason = "service_closed"
        elif gate_slot_elapsed:
            order_gate_reason = "slot_elapsed"
        else:
            order_gate_reason = "open"
    if not order_gate_message:
        if order_gate_reason == "date_mismatch":
            order_gate_message = f"Orders are allowed only for today ({today.isoformat()})."
        elif order_gate_reason == "service_closed":
            order_gate_message = "Food Hall is closed now. Ordering is open from 10:00 AM - 9:00 PM."
        elif order_gate_reason == "slot_elapsed":
            order_gate_message = "Selected slot has already ended. Choose an upcoming slot."

    if demo_enabled:
        evidence.append(_evidence("Demo mode", "Food Hall demo bypass is active", "warning"))
        if selected_slot_label:
            evidence.append(_evidence("Break slot", selected_slot_label, "pass"))
        if cart_signal_present:
            evidence.append(
                _evidence(
                    "Cart",
                    f"{int(cart_item_count or 0)} item(s)",
                    "pass" if has_cart_items else "warning",
                )
            )
        return {
            "blocked": False,
            "title": "Food Hall Demo Mode",
            "explanation": [
                "Food Hall demo bypass is active, so close-time and checkout restrictions are temporarily bypassed.",
                "Live ordering blockers will appear again after demo mode is turned off.",
            ],
            "evidence": evidence,
            "next_steps": [
                "Turn off Demo Bypass when you want the real Food Hall checks back.",
            ],
            "entities": {
                "food": {
                    "ordering_blocked": False,
                    "demo_enabled": True,
                    "order_date": order_date.isoformat(),
                    "selected_slot_id": (int(selected_slot.id) if selected_slot else selected_slot_id),
                }
            },
            "action": _action("food_order_blocker_check", "completed", "Demo bypass active"),
        }

    evidence.append(
        _evidence(
            "Ordering window",
            "Open now" if gate_service_open_now and gate_date_allowed else (order_gate_message or "Closed"),
            "pass" if gate_service_open_now and gate_date_allowed else "fail",
        )
    )
    evidence.append(
        _evidence(
            "Active shops",
            str(active_shop_count),
            "pass" if active_shop_count else "fail",
        )
    )

    if slot_signal_present or selected_slot is not None:
        slot_value = selected_slot_label or "Selected slot unavailable"
        slot_status = "pass"
        if not has_selected_slot:
            slot_value = "Not selected"
            slot_status = "fail"
        elif selected_slot is None and selected_slot_id:
            slot_value = f"Slot #{selected_slot_id} unavailable"
            slot_status = "fail"
        elif gate_slot_elapsed:
            slot_value = selected_slot_label or "Selected slot ended"
            slot_status = "fail"
        evidence.append(_evidence("Break slot", slot_value, slot_status))
        if slot_load_label:
            evidence.append(
                _evidence(
                    "Slot capacity",
                    slot_load_label,
                    "warning" if slot_full else "pass",
                )
            )
    if cart_signal_present:
        cart_label = f"{int(cart_item_count or 0)} item(s)"
        if cart_shop_name:
            cart_label = f"{cart_label} from {cart_shop_name}"
        evidence.append(_evidence("Cart", cart_label, "pass" if has_cart_items else "fail"))
    if checkout_signal_present:
        evidence.append(
            _evidence(
                "Checkout review",
                "Open" if review_open else "Not opened",
                "pass" if review_open else "warning",
            )
        )
        evidence.append(
            _evidence(
                "Delivery block",
                delivery_point or "Not selected",
                "pass" if delivery_point_selected else "warning",
            )
        )
    if location_signal_present:
        if location_checking:
            location_value = "Verification in progress"
            location_status = "warning"
        elif location_verified and location_allowed and location_fresh:
            location_value = location_message or "Campus location verified"
            location_status = "pass"
        else:
            location_value = location_message or "Location not verified"
            location_status = "fail"
        evidence.append(_evidence("Campus location", location_value, location_status))
    if latest_active_order is not None:
        evidence.append(
            _evidence(
                "Active order scope",
                f"{len(active_orders_today)} active order(s) today"
                + (f" with {latest_active_order.shop_name}" if latest_active_order.shop_name else ""),
                "warning",
            )
        )

    if active_shop_count <= 0:
        _append_unique(explanation, "No Food Hall shops are active right now, so new orders cannot start.")
        _append_unique(next_steps, "Activate at least one food shop before retrying checkout.")
    if not gate_date_allowed:
        _append_unique(explanation, order_gate_message)
        _append_unique(next_steps, f"Reset the pickup date to today ({today.isoformat()}) and retry.")
    if not gate_service_open_now:
        _append_unique(explanation, order_gate_message)
        _append_unique(next_steps, "Retry during Food Hall ordering hours: 10:00 AM - 9:00 PM.")
    if slot_signal_present and not has_selected_slot:
        _append_unique(explanation, "Select a break slot before checkout.")
        _append_unique(next_steps, "Choose a current or upcoming break slot in Food Hall.")
    if selected_slot_id and selected_slot is None:
        _append_unique(explanation, "Selected break slot is no longer available. Refresh Food Hall and choose another slot.")
        _append_unique(next_steps, "Refresh Food Hall and select an available break slot again.")
    if selected_slot is not None and selected_slot.start_time < service_start or selected_slot is not None and selected_slot.end_time > service_end:
        _append_unique(explanation, "Selected slot is not open for pickup.")
        _append_unique(next_steps, "Choose a slot that falls inside Food Hall pickup hours.")
    if gate_slot_elapsed:
        _append_unique(explanation, order_gate_message or "Selected slot has already ended. Choose an upcoming slot.")
        _append_unique(next_steps, "Choose an upcoming slot before retrying checkout.")
    if slot_full:
        _append_unique(explanation, "Selected slot is full right now. Choose another slot to avoid congestion.")
        _append_unique(next_steps, "Pick another slot with available capacity.")
    if cart_signal_present and not has_cart_items:
        _append_unique(explanation, "Your cart is empty. Add items from one shop before checkout.")
        _append_unique(next_steps, "Open a shop, add items, then review the cart again.")
    if cart_signal_present and has_cart_items and checkout_signal_present and not review_open:
        _append_unique(explanation, "Open cart and click Review Cart before payment.")
        _append_unique(next_steps, "Open the cart and move to the review step.")
    if cart_signal_present and has_cart_items and checkout_signal_present and review_open and not delivery_point_selected:
        _append_unique(explanation, "Select a delivery block before payment.")
        _append_unique(next_steps, "Choose your delivery block in the checkout review step.")
    if single_shop_conflict:
        other_shops_label = ", ".join(latest_active_shop_names) or "another shop"
        _append_unique(
            explanation,
            f"You already have an active order from {other_shops_label}. Food Hall accepts active orders from one shop at a time.",
        )
        _append_unique(next_steps, "Finish, clear, or complete the current shop order before switching shops.")
    if location_signal_present and cart_signal_present and has_cart_items:
        if location_checking:
            _append_unique(explanation, "Campus location verification is still in progress.")
            _append_unique(next_steps, "Wait for location verification to finish, then retry checkout.")
        elif not location_verified:
            _append_unique(
                explanation,
                location_message or "Enable location access and retry inside LPU campus.",
            )
            _append_unique(next_steps, "Enable location access and verify your position inside LPU campus.")
        elif location_allowed is False:
            _append_unique(
                explanation,
                location_message or "Delivery is allowed only inside LPU campus.",
            )
            _append_unique(next_steps, "Move inside the allowed campus zone, then refresh location verification.")
        elif location_fresh is False:
            _append_unique(
                explanation,
                location_message or "Campus GPS lock expired. Refresh location verification before payment.",
            )
            _append_unique(next_steps, "Refresh your GPS lock before paying.")

    blocked = bool(explanation)
    if not blocked:
        readiness_line = "Food Hall ordering is available in the current session."
        if latest_order is not None and latest_order.status:
            readiness_line += f" Latest order status: {latest_order.status.value}."
        explanation = [
            readiness_line,
            "Continue with Review Cart and payment to place the order.",
        ]
        if not next_steps:
            next_steps = ["Complete payment from the review step to place the order."]

    entities = {
        "food": {
            "ordering_blocked": blocked,
            "demo_enabled": False,
            "order_date": order_date.isoformat(),
            "selected_slot_id": (int(selected_slot.id) if selected_slot else selected_slot_id),
            "selected_slot_label": selected_slot_label or None,
            "cart_item_count": int(cart_item_count or 0),
            "delivery_point_selected": delivery_point_selected,
            "location_verified": bool(location_verified),
            "location_allowed": bool(location_allowed),
            "location_fresh": bool(location_fresh),
            "active_shops": active_shop_count,
            "active_orders_today": len(active_orders_today),
            "single_shop_conflict": single_shop_conflict,
            "slot_full": slot_full,
            "order_gate_reason": order_gate_reason or None,
            "client_context_used": bool(food_context),
            "latest_status": latest_order.status.value if latest_order is not None else None,
        }
    }
    return {
        "blocked": blocked,
        "title": "Food Ordering Blocked" if blocked else "Food Ordering Ready",
        "explanation": explanation,
        "evidence": evidence,
        "next_steps": next_steps,
        "entities": entities,
        "action": _action(
            "food_order_blocker_check",
            "blocked" if blocked else "completed",
            explanation[0] if explanation else "Food ordering check completed",
        ),
    }


def _extract_first_int(regex: re.Pattern[str], text: str) -> int | None:
    match = regex.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _extract_registration_candidate(text: str) -> str | None:
    explicit = REGISTRATION_RE.search(text)
    if explicit:
        candidate = re.sub(r"\s+", "", explicit.group(1).strip().upper())
        return candidate or None
    for token in re.findall(r"[A-Z0-9/-]{5,40}", text.upper()):
        if any(char.isalpha() for char in token) and any(char.isdigit() for char in token):
            return token
    return None


def _extract_section(text: str) -> str | None:
    match = SECTION_RE.search(text)
    if not match:
        return None
    try:
        return _normalize_sections([match.group(1)])[0]
    except HTTPException:
        return None


def _extract_course_code(text: str) -> str | None:
    match = COURSE_CODE_RE.search(text)
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(1).strip().upper()) or None


def _extract_room_number(text: str) -> str | None:
    match = ROOM_RE.search(text)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1).strip()) or None


def _extract_date(text: str) -> date | None:
    match = DATE_RE.search(text)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _extract_times(text: str) -> list[time]:
    out: list[time] = []
    for hour_raw, minute_raw in TIME_RE.findall(text):
        try:
            out.append(time(hour=int(hour_raw), minute=int(minute_raw)))
        except ValueError:
            continue
    return out


def _normalize_registration_number(value: str | None) -> str | None:
    normalized = re.sub(r"\s+", "", str(value or "").strip().upper())
    if not normalized:
        return None
    if len(normalized) < 3 or not REGISTRATION_PATTERN.fullmatch(normalized):
        return None
    return normalized


def _resolve_intent(query_text: str) -> schemas.CopilotIntent:
    normalized = re.sub(r"\s+", " ", str(query_text or "").strip().lower())
    if not normalized:
        return schemas.CopilotIntent.UNSUPPORTED

    def _looks_like_attendance_blocker_query() -> bool:
        if "attendance" not in normalized:
            return False
        explicit_phrases = (
            "attendance blocked",
            "attendance isn't getting marked",
            "attendance isnt getting marked",
            "attendance is not getting marked",
            "attendance not getting marked",
            "attendance isn't marked",
            "attendance isnt marked",
            "attendance is not marked",
            "attendance not marked",
            "attendance not marking",
            "attendance isn't marking",
            "attendance isnt marking",
            "attendance failed to mark",
            "attendance not updating",
            "attendance isn't updating",
            "attendance isnt updating",
            "attendance not showing",
            "attendance isn't showing",
            "attendance isnt showing",
            "attendance not reflecting",
            "attendance issue",
            "attendance problem",
            "attendance error",
        )
        if any(phrase in normalized for phrase in explicit_phrases):
            return True

        blocker_markers = (
            "can't",
            "cannot",
            "unable",
            "won't",
            "wont",
            "isn't",
            "isnt",
            "not",
            "blocked",
            "issue",
            "problem",
            "error",
            "failed",
            "failing",
            "stuck",
            "why",
        )
        attendance_flow_markers = (
            "mark",
            "marked",
            "marking",
            "capture",
            "captured",
            "capturing",
            "verify",
            "verified",
            "verification",
            "record",
            "recorded",
            "recording",
            "showing",
            "updating",
            "updated",
            "reflecting",
            "reflect",
            "sync",
            "synced",
            "selfie",
        )
        return (
            any(marker in normalized for marker in blocker_markers)
            and any(marker in normalized for marker in attendance_flow_markers)
        )

    if "remedial" in normalized and any(token in normalized for token in ("create", "plan", "schedule")):
        return schemas.CopilotIntent.CREATE_REMEDIAL_PLAN
    if "eligibility" in normalized or "lose eligibility" in normalized or "attendance shortage" in normalized:
        return schemas.CopilotIntent.ELIGIBILITY_RISK
    if "flagged" in normalized and any(token in normalized for token in ("student", "show", "why")):
        return schemas.CopilotIntent.STUDENT_FLAG_REASON
    if "mark attendance" in normalized or _looks_like_attendance_blocker_query():
        return schemas.CopilotIntent.ATTENDANCE_BLOCKER
    return schemas.CopilotIntent.MODULE_ASSIST


def _evidence(label: str, value: str, status: str = "info") -> schemas.CopilotEvidenceItem:
    return schemas.CopilotEvidenceItem(label=label, value=value, status=status)


def _action(action: str, status: str, detail: str | None = None) -> schemas.CopilotActionItem:
    return schemas.CopilotActionItem(action=action, status=status, detail=detail)


def _serialize_audit_row(
    row: models.CopilotAuditLog,
    *,
    actor_email: str | None = None,
) -> schemas.CopilotAuditLogOut:
    return schemas.CopilotAuditLogOut(
        id=int(row.id),
        actor_user_id=int(row.actor_user_id),
        actor_role=str(row.actor_role or ""),
        actor_email=(str(actor_email or "").strip() or None),
        query_text=str(row.query_text or ""),
        intent=schemas.CopilotIntent(str(row.intent or schemas.CopilotIntent.UNSUPPORTED.value)),
        outcome=schemas.CopilotOutcome(str(row.outcome or schemas.CopilotOutcome.FAILED.value)),
        scope=(str(row.scope or "").strip() or None),
        target_student_id=(int(row.target_student_id) if row.target_student_id else None),
        target_course_id=(int(row.target_course_id) if row.target_course_id else None),
        target_section=(str(row.target_section or "").strip() or None),
        explanation=[str(item) for item in _safe_json_load_dict(row.result_json).get("explanation", []) if str(item).strip()],
        evidence=[schemas.CopilotEvidenceItem(**item) for item in _safe_json_load_list(row.evidence_json)],
        actions=[schemas.CopilotActionItem(**item) for item in _safe_json_load_list(row.actions_json)],
        result=_safe_json_load_dict(row.result_json),
        created_at=row.created_at or datetime.utcnow(),
    )


def _persist_audit(
    db: Session,
    *,
    current_user: CurrentUser,
    payload: schemas.CopilotQueryRequest,
    response: schemas.CopilotQueryResponse,
    scope: str | None,
    target_student_id: int | None = None,
    target_course_id: int | None = None,
    target_section: str | None = None,
) -> schemas.CopilotQueryResponse:
    def _copilot_sql_only_audit() -> bool:
        raw = (os.getenv("COPILOT_SQL_ONLY_AUDIT", "true") or "").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _audit_failure_response(detail: str | None = None) -> schemas.CopilotQueryResponse:
        # Keep primary answer available even if audited write is temporarily unavailable.
        response.actions = list(response.actions)
        response.actions.append(
            _action(
                "copilot_audit_log",
                "failed",
                detail or "Audit logging skipped due to datastore sync issue.",
            )
        )
        response.audit_id = None
        return response

    def _audit_fk_actor_missing(exc: Exception) -> bool:
        normalized = str(exc).lower()
        return (
            "foreign key" in normalized
            and "actor_user_id" in normalized
            and ("copilot_audit_logs" in normalized or "copilot_audit_logs_actor_user_id_fkey" in normalized)
        )

    def _resolve_actor_email() -> str:
        normalized = str(current_user.email or "").strip().lower()
        if normalized:
            return normalized
        return f"copilot-user-{int(current_user.id)}@local.invalid"

    def _ensure_actor_sql_shadow() -> None:
        actor_id = int(current_user.id)
        actor = db.get(models.AuthUser, actor_id)
        actor_email = _resolve_actor_email()
        if actor is None:
            email_conflict = (
                db.query(models.AuthUser.id)
                .filter(
                    func.lower(models.AuthUser.email) == actor_email,
                    models.AuthUser.id != actor_id,
                )
                .first()
            )
            if email_conflict:
                actor_email = f"copilot-user-{actor_id}@local.invalid"

            db.add(
                models.AuthUser(
                    id=actor_id,
                    email=actor_email,
                    # Placeholder only for FK integrity; real auth is Mongo-backed.
                    password_hash="copilot-audit-placeholder",
                    role=current_user.role,
                    student_id=None,
                    faculty_id=None,
                    is_active=bool(current_user.is_active),
                    last_login_at=current_user.last_login_at,
                )
            )
            db.flush()
            sync_auth_user_pk_sequence(db)
            return

        changed = False
        if actor.role != current_user.role:
            actor.role = current_user.role
            changed = True
        if actor_email and actor.email != actor_email:
            email_conflict = (
                db.query(models.AuthUser.id)
                .filter(
                    func.lower(models.AuthUser.email) == actor_email,
                    models.AuthUser.id != actor.id,
                )
                .first()
            )
            if not email_conflict:
                actor.email = actor_email
                changed = True
        if actor.is_active != bool(current_user.is_active):
            actor.is_active = bool(current_user.is_active)
            changed = True
        if current_user.last_login_at and (
            actor.last_login_at is None or current_user.last_login_at > actor.last_login_at
        ):
            actor.last_login_at = current_user.last_login_at
            changed = True
        if changed:
            db.flush()

    try:
        _ensure_actor_sql_shadow()
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception(
            "copilot_actor_shadow_sync_failed actor_user_id=%s role=%s",
            current_user.id,
            current_user.role.value,
        )
        return _audit_failure_response("Audit skipped because actor sync failed.")

    row = models.CopilotAuditLog(
        actor_user_id=int(current_user.id),
        actor_role=current_user.role.value,
        session_id=(str(current_user.session_id or "").strip() or None),
        query_text=str(payload.query_text or "").strip(),
        intent=response.intent.value,
        outcome=response.outcome.value,
        scope=scope,
        target_student_id=target_student_id,
        target_course_id=target_course_id,
        target_section=target_section,
        explanation_json=_safe_json_dump(response.explanation),
        evidence_json=_safe_json_dump([item.model_dump() for item in response.evidence]),
        actions_json=_safe_json_dump([item.model_dump() for item in response.actions]),
        result_json=_safe_json_dump(
            {
                "title": response.title,
                "explanation": response.explanation,
                "next_steps": response.next_steps,
                "entities": response.entities,
            }
        ),
        created_at=datetime.utcnow(),
    )
    for attempt in range(2):
        try:
            db.add(row)
            db.commit()
            db.refresh(row)
            break
        except IntegrityError as exc:
            db.rollback()
            if attempt == 0 and _audit_fk_actor_missing(exc):
                try:
                    _ensure_actor_sql_shadow()
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "copilot_actor_shadow_resync_failed actor_user_id=%s role=%s",
                        current_user.id,
                        current_user.role.value,
                    )
                    return _audit_failure_response("Audit skipped because actor sync failed.")
                continue
            logger.exception(
                "copilot_audit_integrity_error actor_user_id=%s role=%s",
                current_user.id,
                current_user.role.value,
            )
            return _audit_failure_response("Audit logging failed due to database integrity rules.")
        except SQLAlchemyError:
            db.rollback()
            logger.exception(
                "copilot_audit_sql_error actor_user_id=%s role=%s",
                current_user.id,
                current_user.role.value,
            )
            return _audit_failure_response("Audit logging is temporarily unavailable.")
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.exception(
                "copilot_audit_unexpected_error actor_user_id=%s role=%s",
                current_user.id,
                current_user.role.value,
            )
            return _audit_failure_response("Audit logging is temporarily unavailable.")

    response.audit_id = int(row.id)
    if _copilot_sql_only_audit():
        return response
    try:
        mirror_document(
            "admin_audit_logs",
            {
                "action": "campus_copilot_query",
                "audit_id": int(row.id),
                "intent": response.intent.value,
                "outcome": response.outcome.value,
                "query_text": row.query_text,
                "scope": row.scope,
                "target_student_id": row.target_student_id,
                "target_course_id": row.target_course_id,
                "target_section": row.target_section,
                "created_at": row.created_at,
                "source": "copilot.query",
                "actor_user_id": current_user.id,
                "actor_role": current_user.role.value,
            },
            required=False,
        )
        mirror_event(
            "copilot.query.processed",
            {
                "audit_id": int(row.id),
                "intent": response.intent.value,
                "outcome": response.outcome.value,
                "scope": row.scope,
                "target_student_id": row.target_student_id,
                "target_course_id": row.target_course_id,
                "target_section": row.target_section,
            },
            actor={
                "user_id": int(current_user.id),
                "role": current_user.role.value,
                "student_id": current_user.student_id,
                "faculty_id": current_user.faculty_id,
            },
            source="copilot.query",
            required=False,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "copilot_audit_mirror_failed audit_id=%s actor_user_id=%s",
            getattr(row, "id", None),
            current_user.id,
        )
    return response


def _student_section_token(student: models.Student | None) -> str:
    if not student:
        return ""
    return re.sub(r"\s+", "", str(student.section or "").strip().upper())


def _faculty_can_manage_student_scope(db: Session, *, faculty_id: int, student: models.Student | None) -> bool:
    if not student:
        return False
    faculty = db.get(models.Faculty, int(faculty_id))
    allowed_sections = remedial_faculty_allowed_sections(faculty)
    student_section = _student_section_token(student)
    if allowed_sections:
        return bool(student_section and student_section in allowed_sections)
    teaches_student = (
        db.query(models.Enrollment.id)
        .join(models.Course, models.Course.id == models.Enrollment.course_id)
        .filter(
            models.Enrollment.student_id == int(student.id),
            models.Course.faculty_id == int(faculty_id),
        )
        .first()
        is not None
    )
    return teaches_student


def _student_today_regular_schedules(db: Session, *, student: models.Student) -> list[models.ClassSchedule]:
    today = date.today()
    enrollment_rows = (
        db.query(models.Enrollment.course_id)
        .filter(models.Enrollment.student_id == int(student.id))
        .all()
    )
    course_ids = sorted({int(row.course_id) for row in enrollment_rows if row and row.course_id})
    if not course_ids:
        return []

    schedules = (
        db.query(models.ClassSchedule)
        .filter(
            models.ClassSchedule.is_active.is_(True),
            models.ClassSchedule.course_id.in_(course_ids),
            models.ClassSchedule.weekday == int(today.weekday()),
        )
        .order_by(models.ClassSchedule.start_time.asc(), models.ClassSchedule.id.asc())
        .all()
    )
    student_section = _student_section_token(student)
    override_filters = [
        (
            (models.TimetableOverride.scope_type == schemas.TimetableOverrideScope.STUDENT.value)
            & (models.TimetableOverride.student_id == int(student.id))
        )
    ]
    if student_section:
        override_filters.append(
            (
                (models.TimetableOverride.scope_type == schemas.TimetableOverrideScope.SECTION.value)
                & (models.TimetableOverride.section == student_section)
            )
        )
    overrides = (
        db.query(models.TimetableOverride)
        .filter(models.TimetableOverride.is_active.is_(True), or_(*override_filters))
        .order_by(models.TimetableOverride.created_at.asc(), models.TimetableOverride.id.asc())
        .all()
    )
    override_schedule_ids = sorted({int(item.schedule_id) for item in overrides if item.schedule_id})
    override_schedules = (
        {
            int(row.id): row
            for row in db.query(models.ClassSchedule)
            .filter(models.ClassSchedule.id.in_(override_schedule_ids))
            .all()
        }
        if override_schedule_ids
        else {}
    )

    effective_overrides: dict[tuple[int, time], models.ClassSchedule] = {}
    for override in overrides:
        target_schedule = override_schedules.get(int(override.schedule_id))
        if not target_schedule or not target_schedule.is_active:
            continue
        effective_overrides[(int(override.source_weekday), override.source_start_time)] = target_schedule

    suppressed_slots = set(effective_overrides.keys())
    override_target_ids = {int(item.id) for item in effective_overrides.values()}
    visible: list[models.ClassSchedule] = []
    for schedule in schedules:
        slot_key = (int(schedule.weekday), schedule.start_time)
        if slot_key in suppressed_slots or int(schedule.id) in override_target_ids:
            continue
        visible.append(schedule)
    for schedule in effective_overrides.values():
        if int(schedule.weekday) == int(today.weekday()):
            visible.append(schedule)
    visible.sort(key=lambda row: (row.start_time, row.id))
    return visible


def _pick_target_schedule(
    db: Session,
    *,
    student: models.Student,
    schedule_id: int | None,
    course_code: str | None,
) -> tuple[models.ClassSchedule | None, models.Course | None, str | None]:
    today = date.today()
    if schedule_id:
        schedule = db.get(models.ClassSchedule, int(schedule_id))
        if not schedule or not schedule.is_active:
            return None, None, "Class schedule not found."
        course = db.get(models.Course, int(schedule.course_id))
        if not course:
            return None, None, "Course not found for the selected schedule."
        return schedule, course, None

    schedules = _student_today_regular_schedules(db, student=student)
    courses_by_id = {
        int(row.id): row
        for row in db.query(models.Course)
        .filter(models.Course.id.in_([int(item.course_id) for item in schedules]))
        .all()
    } if schedules else {}
    if course_code:
        schedules = [item for item in schedules if str(courses_by_id.get(int(item.course_id)).code or "").upper() == course_code]

    if not schedules:
        if course_code:
            return None, None, f"No active class for course {course_code} is scheduled today."
        return None, None, "No active class is scheduled for you today."

    now_dt = datetime.now()
    open_now = [row for row in schedules if _window_flags(row, now_dt, today)[0]]
    if len(open_now) == 1:
        chosen = open_now[0]
        return chosen, courses_by_id.get(int(chosen.course_id)), None
    if len(open_now) > 1:
        return None, None, "Multiple attendance windows are open. Specify schedule id to continue."

    active_now = [row for row in schedules if _window_flags(row, now_dt, today)[1]]
    if len(active_now) == 1:
        chosen = active_now[0]
        return chosen, courses_by_id.get(int(chosen.course_id)), None
    if len(active_now) > 1:
        return None, None, "Multiple classes are currently active. Specify schedule id to continue."

    if len(schedules) == 1:
        chosen = schedules[0]
        return chosen, courses_by_id.get(int(chosen.course_id)), None

    return None, None, "More than one class matches today. Specify schedule id or course code."


def _classes_needed_to_recover(attended: int, delivered: int) -> int:
    deficit = (3 * int(delivered)) - (4 * int(attended))
    return max(0, deficit)


def _safe_absences_remaining(attended: int, delivered: int) -> int:
    if delivered <= 0:
        return 0
    value = math.floor((float(attended) / 0.75) - float(delivered))
    return max(0, int(value))


def _faux_student_user(actor: CurrentUser, student_id: int) -> CurrentUser:
    return CurrentUser(
        id=int(actor.id),
        email=str(actor.email or ""),
        role=models.UserRole.STUDENT,
        student_id=int(student_id),
        faculty_id=None,
        alternate_email=None,
        primary_login_verified=True,
        is_active=True,
        mfa_enabled=False,
        mfa_authenticated=True,
        session_id=actor.session_id,
        token_jti=actor.token_jti,
        device_id=actor.device_id,
        created_at=actor.created_at,
        last_login_at=actor.last_login_at,
    )


def _attendance_blocker_response(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[schemas.CopilotQueryResponse, dict[str, Any]]:
    if current_user.role != models.UserRole.STUDENT:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.ATTENDANCE_BLOCKER,
                outcome=schemas.CopilotOutcome.DENIED,
                title="Attendance Check Restricted",
                explanation=["Only student accounts can run self-service attendance blocker checks."],
                next_steps=_supported_queries_for_role(current_user.role),
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    evidence: list[schemas.CopilotEvidenceItem] = []
    blockers: list[str] = []
    course_code = payload.course_code or _extract_course_code(payload.query_text)
    schedule_id = payload.schedule_id or _extract_first_int(SCHEDULE_ID_RE, payload.query_text)

    if not current_user.student_id:
        blockers.append("Student account is not linked correctly.")
        response = schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.ATTENDANCE_BLOCKER,
            outcome=schemas.CopilotOutcome.BLOCKED,
            title="Attendance Blocked",
            explanation=blockers,
            evidence=[_evidence("Account linkage", "Student account link missing", "fail")],
        )
        return response, {"scope": "student:unlinked"}

    student = db.get(models.Student, int(current_user.student_id))
    if not student:
        response = schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.ATTENDANCE_BLOCKER,
            outcome=schemas.CopilotOutcome.BLOCKED,
            title="Attendance Blocked",
            explanation=["Student record was not found."],
            evidence=[_evidence("Student record", "Missing", "fail")],
        )
        return response, {"scope": f"student:{int(current_user.student_id)}", "target_student_id": int(current_user.student_id)}

    evidence.append(_evidence("Student", f"{student.name} ({student.email})"))
    has_registration = bool(str(student.registration_number or "").strip())
    evidence.append(
        _evidence(
            "Registration number",
            (str(student.registration_number or "").strip().upper() or "Missing"),
            "pass" if has_registration else "fail",
        )
    )
    if not has_registration:
        blockers.append("Complete profile setup with registration number before attendance.")

    has_profile_photo = bool(student.profile_photo_object_key or student.profile_photo_data_url)
    evidence.append(
        _evidence(
            "Profile photo",
            "On file" if has_profile_photo else "Missing",
            "pass" if has_profile_photo else "fail",
        )
    )
    if not has_profile_photo:
        blockers.append("Upload profile photo before marking attendance.")

    has_enrollment_video = bool(str(student.enrollment_video_template_json or "").strip())
    evidence.append(
        _evidence(
            "Enrollment video",
            "Completed" if has_enrollment_video else "Missing",
            "pass" if has_enrollment_video else "fail",
        )
    )
    if not has_enrollment_video:
        blockers.append("Complete one-time enrollment video before marking attendance.")

    schedule, course, pick_error = _pick_target_schedule(
        db,
        student=student,
        schedule_id=schedule_id,
        course_code=course_code,
    )
    if pick_error:
        blockers.append(pick_error)

    if schedule and course:
        evidence.append(
            _evidence(
                "Target class",
                f"{course.code} | schedule {int(schedule.id)} | {schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}",
            )
        )
        if not blockers:
            try:
                _resolve_student_schedule_context(
                    db=db,
                    current_user=current_user,
                    schedule_id=int(schedule.id),
                )
                evidence.append(_evidence("Timetable scope", "Class is assigned in your active timetable", "pass"))
                evidence.append(_evidence("Enrollment", "You are enrolled in this class", "pass"))
            except HTTPException as exc:
                blockers.append(str(exc.detail))
                message = str(exc.detail or "")
                if "timetable" in message.lower():
                    evidence.append(_evidence("Timetable scope", message, "fail"))
                elif "enrolled" in message.lower():
                    evidence.append(_evidence("Enrollment", message, "fail"))
                else:
                    evidence.append(_evidence("Class access", message, "fail"))

        today = date.today()
        now_dt = datetime.now()
        if schedule.weekday != int(today.weekday()):
            blockers.append("This class is not scheduled for today.")
            evidence.append(_evidence("Class day", "Not scheduled today", "fail"))
        else:
            is_open_now, is_active_now, _ = _window_flags(schedule, now_dt, today, course=course)
            if is_open_now:
                evidence.append(_evidence("Attendance window", "Open now", "pass"))
            else:
                detail = "Attendance window is closed (only first 10 minutes)." if is_active_now else "Attendance is not open yet."
                blockers.append(detail)
                evidence.append(_evidence("Attendance window", detail, "fail"))

    if blockers:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.ATTENDANCE_BLOCKER,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Attendance Blocked",
                explanation=blockers,
                evidence=evidence,
                actions=[_action("attendance_mark_check", "blocked", blockers[0])],
                next_steps=[
                    "Fix the failed checks above, then retry attendance marking from the Attendance module.",
                    "If multiple classes are running today, include schedule id or course code in your prompt.",
                ],
                entities={
                    "student_id": int(student.id),
                    "schedule_id": int(schedule.id) if schedule else None,
                    "course_id": int(course.id) if course else None,
                    "course_code": (course.code if course else None),
                },
            ),
            {
                "scope": f"student:{int(student.id)}",
                "target_student_id": int(student.id),
                "target_course_id": int(course.id) if course else None,
            },
        )

    return (
        schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.ATTENDANCE_BLOCKER,
            outcome=schemas.CopilotOutcome.COMPLETED,
            title="Attendance Ready",
            explanation=[
                f"You can mark attendance for {course.code} right now.",
                "No policy blocker is active. The remaining step is live face verification in the attendance capture flow.",
            ],
            evidence=evidence,
            actions=[_action("attendance_mark_check", "completed", "All pre-checks passed")],
            next_steps=["Open the live attendance flow and complete the selfie verification."],
            entities={
                "student_id": int(student.id),
                "schedule_id": int(schedule.id),
                "course_id": int(course.id),
                "course_code": course.code,
            },
        ),
        {
            "scope": f"student:{int(student.id)}",
            "target_student_id": int(student.id),
            "target_course_id": int(course.id),
        },
    )


def _eligibility_risk_response(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[schemas.CopilotQueryResponse, dict[str, Any]]:
    if current_user.role != models.UserRole.STUDENT:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.ELIGIBILITY_RISK,
                outcome=schemas.CopilotOutcome.DENIED,
                title="Eligibility Check Restricted",
                explanation=["Only student accounts can run self-service eligibility checks."],
                next_steps=_supported_queries_for_role(current_user.role),
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    aggregate = get_student_attendance_aggregate(db=db, current_user=current_user)
    requested_course_code = payload.course_code or _extract_course_code(payload.query_text)
    course_rows = aggregate.courses
    if requested_course_code:
        course_rows = [row for row in aggregate.courses if row.course_code == requested_course_code]
        if not course_rows:
            response = schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.ELIGIBILITY_RISK,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Eligibility Scope Not Found",
                explanation=[f"No attendance aggregate was found for course {requested_course_code}."],
                next_steps=["Retry with a valid enrolled course code or remove the course filter."],
            )
            return response, {"scope": f"student:{int(current_user.student_id or 0)}"}

    evidence = [
        _evidence("Overall attendance", f"{aggregate.aggregate_percent:.2f}% ({aggregate.attended_total}/{aggregate.delivered_total})"),
    ]
    explanations = [f"Your current aggregate attendance is {aggregate.aggregate_percent:.2f}%."]
    next_steps: list[str] = []
    at_risk_lines: list[str] = []
    watch_lines: list[str] = []
    stable_lines: list[str] = []

    for row in course_rows:
        safe_misses = _safe_absences_remaining(row.attended_classes, row.delivered_classes)
        recover = _classes_needed_to_recover(row.attended_classes, row.delivered_classes)
        evidence.append(
            _evidence(
                f"{row.course_code}",
                f"{row.attendance_percent:.2f}% ({row.attended_classes}/{row.delivered_classes})",
                "fail" if row.delivered_classes >= 4 and row.attendance_percent < 75.0 else (
                    "warning" if row.attendance_percent < 80.0 else "pass"
                ),
            )
        )
        if row.delivered_classes >= 4 and row.attendance_percent < 75.0:
            at_risk_lines.append(
                f"{row.course_code} is below 75%. Attend the next {recover} class(es) in a row to recover eligibility."
            )
        elif row.delivered_classes > 0 and row.attendance_percent < 80.0:
            watch_lines.append(
                f"{row.course_code} is on watch at {row.attendance_percent:.2f}%. You can miss {safe_misses} more class(es) before dropping below 75%."
            )
        else:
            stable_lines.append(
                f"{row.course_code} is stable at {row.attendance_percent:.2f}%. Safe misses remaining before 75%: {safe_misses}."
            )

    if at_risk_lines:
        explanations.append(f"You are already below the 75% threshold in {len(at_risk_lines)} course(s).")
        explanations.extend(at_risk_lines)
        next_steps.append("Prioritize the flagged courses first; the recovery counts above assume no further absences.")
        title = "Eligibility At Risk"
    elif watch_lines:
        explanations.append("You are still eligible, but one or more courses are close to the 75% boundary.")
        explanations.extend(watch_lines)
        if stable_lines:
            explanations.extend(stable_lines[:2])
        next_steps.append("Do not miss the next scheduled class in the watchlisted course(s).")
        title = "Eligibility Watchlist"
    else:
        explanations.append("No course is currently below the 75% eligibility threshold.")
        explanations.extend(stable_lines[:3] or ["Keep maintaining your current attendance pace."])
        next_steps.append("Keep your attendance above 75% in every course, not just the aggregate.")
        title = "Eligibility Safe"

    return (
        schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.ELIGIBILITY_RISK,
            outcome=schemas.CopilotOutcome.COMPLETED,
            title=title,
            explanation=explanations,
            evidence=evidence,
            actions=[_action("eligibility_risk_check", "completed", f"Reviewed {len(course_rows)} course aggregate(s)")],
            next_steps=next_steps,
            entities={
                "student_id": int(current_user.student_id or 0),
                "aggregate_percent": float(aggregate.aggregate_percent),
                "at_risk_courses": [row.course_code for row in course_rows if row.delivered_classes >= 4 and row.attendance_percent < 75.0],
            },
        ),
        {
            "scope": f"student:{int(current_user.student_id or 0)}",
            "target_student_id": int(current_user.student_id or 0),
        },
    )


def _resolve_target_student(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[models.Student | None, str | None]:
    student_id = payload.student_id or _extract_first_int(STUDENT_ID_RE, payload.query_text)
    registration_number = _normalize_registration_number(payload.registration_number) or _normalize_registration_number(
        _extract_registration_candidate(payload.query_text)
    )
    student = None
    if student_id:
        student = db.get(models.Student, int(student_id))
    elif registration_number:
        student = (
            db.query(models.Student)
            .filter(func.upper(models.Student.registration_number) == registration_number)
            .first()
        )
    if not student:
        if student_id or registration_number:
            return None, "Student not found in the current campus record set."
        return None, "Provide a student id or registration number."

    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            return None, "Faculty account is not linked correctly."
        if not _faculty_can_manage_student_scope(db, faculty_id=int(current_user.faculty_id), student=student):
            return None, "Student is outside your allocated section(s) and teaching scope."
    return student, None


def _flag_reason_response(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[schemas.CopilotQueryResponse, dict[str, Any]]:
    if current_user.role not in {models.UserRole.ADMIN, models.UserRole.FACULTY}:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.STUDENT_FLAG_REASON,
                outcome=schemas.CopilotOutcome.DENIED,
                title="Student Flag Review Restricted",
                explanation=["Only admin and faculty accounts can inspect another student's flag reasons."],
                next_steps=_supported_queries_for_role(current_user.role),
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    student, error = _resolve_target_student(payload, db=db, current_user=current_user)
    if error:
        outcome = schemas.CopilotOutcome.DENIED if "outside your allocated" in error.lower() else schemas.CopilotOutcome.BLOCKED
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.STUDENT_FLAG_REASON,
                outcome=outcome,
                title="Student Flag Review Blocked",
                explanation=[error],
                next_steps=["Retry with a valid in-scope student id or registration number."],
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    _ensure_student_rms_cases(db, student_id=int(student.id), limit=800)
    aggregate = get_student_attendance_aggregate(db=db, current_user=_faux_student_user(current_user, int(student.id)))
    at_risk_courses = [row for row in aggregate.courses if row.delivered_classes >= 4 and row.attendance_percent < 75.0]
    open_cases = (
        db.query(models.RMSCase)
        .filter(
            models.RMSCase.student_id == int(student.id),
            models.RMSCase.status != models.RMSCaseStatus.CLOSED,
        )
        .order_by(models.RMSCase.updated_at.desc(), models.RMSCase.id.desc())
        .all()
    )
    escalated_cases = [row for row in open_cases if bool(row.is_escalated)]
    pending_rectifications = int(
        db.query(func.count(models.AttendanceRectificationRequest.id))
        .filter(
            models.AttendanceRectificationRequest.student_id == int(student.id),
            models.AttendanceRectificationRequest.status == models.AttendanceRectificationStatus.PENDING,
        )
        .scalar()
        or 0
    )
    pending_corrections = int(
        db.query(func.count(models.RMSAttendanceCorrectionRequest.id))
        .filter(
            models.RMSAttendanceCorrectionRequest.student_id == int(student.id),
            models.RMSAttendanceCorrectionRequest.status
            == models.RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL,
        )
        .scalar()
        or 0
    )
    missing_profile_flags: list[str] = []
    if not str(student.registration_number or "").strip():
        missing_profile_flags.append("registration number missing")
    if not _student_section_token(student):
        missing_profile_flags.append("section missing")
    if not (student.profile_photo_object_key or student.profile_photo_data_url):
        missing_profile_flags.append("profile photo missing")

    evidence = [
        _evidence("Student", f"{student.name} ({student.registration_number or 'No reg'})"),
        _evidence("Overall attendance", f"{aggregate.aggregate_percent:.2f}% ({aggregate.attended_total}/{aggregate.delivered_total})"),
        _evidence("Open RMS cases", str(len(open_cases)), "warning" if open_cases else "pass"),
        _evidence("Escalated RMS cases", str(len(escalated_cases)), "fail" if escalated_cases else "pass"),
        _evidence("Pending rectification requests", str(pending_rectifications), "warning" if pending_rectifications else "pass"),
        _evidence("Pending attendance corrections", str(pending_corrections), "warning" if pending_corrections else "pass"),
    ]
    if missing_profile_flags:
        evidence.append(_evidence("Profile completeness", ", ".join(missing_profile_flags), "warning"))

    reasons: list[str] = []
    next_steps: list[str] = []
    for row in at_risk_courses:
        recover = _classes_needed_to_recover(row.attended_classes, row.delivered_classes)
        reasons.append(
            f"{row.course_code} is below 75% at {row.attendance_percent:.2f}% and needs {recover} consecutive attended class(es) to recover."
        )
    if escalated_cases:
        reasons.append(f"{len(escalated_cases)} RMS case(s) are escalated and still unresolved.")
        next_steps.append("Review the escalated RMS case queue and transition or close the open case(s).")
    elif open_cases:
        reasons.append(f"{len(open_cases)} RMS case(s) are still open for this student.")
        next_steps.append("Triage the open RMS case(s) so the student exits the unresolved support queue.")
    if pending_rectifications:
        reasons.append(f"{pending_rectifications} attendance rectification request(s) are pending faculty review.")
        next_steps.append("Review the pending attendance rectification request(s).")
    if pending_corrections:
        reasons.append(f"{pending_corrections} RMS attendance correction request(s) are pending admin approval.")
        next_steps.append("Review the pending attendance correction request(s).")
    if missing_profile_flags:
        reasons.append("Profile completeness checks are failing: " + ", ".join(missing_profile_flags) + ".")
        next_steps.append("Update the missing profile attributes so identity checks stop failing.")

    if at_risk_courses:
        next_steps.append(
            f"Consider a remedial plan for {at_risk_courses[0].course_code} if the attendance deficit is not recoverable through the next regular classes."
        )

    if reasons:
        explanation = [f"{student.name} is flagged for {len(reasons)} active reason(s).", *reasons]
        title = "Student Flag Reasons"
    else:
        explanation = [f"No active flag reasons were found for {student.name}."]
        title = "Student Not Flagged"
        next_steps.append("No intervention is required right now.")

    return (
        schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.STUDENT_FLAG_REASON,
            outcome=schemas.CopilotOutcome.COMPLETED,
            title=title,
            explanation=explanation,
            evidence=evidence,
            actions=[_action("student_flag_review", "completed", f"Reviewed student {int(student.id)}")],
            next_steps=next_steps,
            entities={
                "student_id": int(student.id),
                "registration_number": (str(student.registration_number or "").strip().upper() or None),
                "at_risk_courses": [row.course_code for row in at_risk_courses],
                "open_rms_cases": len(open_cases),
                "pending_rectifications": pending_rectifications,
                "pending_corrections": pending_corrections,
            },
        ),
        {
            "scope": f"student:{int(student.id)}",
            "target_student_id": int(student.id),
        },
    )


def _resolve_remedial_course(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[models.Course | None, str | None]:
    course_id = payload.course_id or _extract_first_int(COURSE_ID_RE, payload.query_text)
    course_code = payload.course_code or _extract_course_code(payload.query_text)
    query = db.query(models.Course)
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            return None, "Faculty account is not linked correctly."
        query = query.filter(models.Course.faculty_id == int(current_user.faculty_id))

    if course_id:
        course = query.filter(models.Course.id == int(course_id)).first()
        return course, None if course else "Course was not found in your allowed scope."
    if course_code:
        course = query.filter(func.upper(models.Course.code) == course_code).first()
        return course, None if course else f"Course {course_code} was not found in your allowed scope."

    candidate_courses = query.order_by(models.Course.code.asc(), models.Course.id.asc()).all()
    if len(candidate_courses) == 1:
        return candidate_courses[0], None
    return None, "Specify course id or course code for the remedial plan."


def _resolve_target_section(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[str | None, str | None]:
    section = payload.section or _extract_section(payload.query_text)
    if current_user.role == models.UserRole.FACULTY:
        if not current_user.faculty_id:
            return None, "Faculty account is not linked correctly."
        faculty = db.get(models.Faculty, int(current_user.faculty_id))
        allowed_sections = sorted(remedial_faculty_allowed_sections(faculty))
        if section:
            if allowed_sections and section not in allowed_sections:
                return None, "Selected section is outside your allocated section scope."
            return section, None
        if len(allowed_sections) == 1:
            return allowed_sections[0], None
        return None, "Specify section for the remedial plan."
    if section:
        return section, None
    return None, "Specify section for the remedial plan."


def _resolve_remedial_schedule_inputs(payload: schemas.CopilotQueryRequest) -> tuple[date | None, time | None, time | None, str, str | None, list[str]]:
    class_date = payload.class_date or _extract_date(payload.query_text)
    query_times = _extract_times(payload.query_text)
    start_time = payload.start_time or (query_times[0] if query_times else None)
    end_time = payload.end_time or (query_times[1] if len(query_times) > 1 else None)
    mode = payload.class_mode or ("offline" if "offline" in payload.query_text.lower() else "online")
    room_number = payload.room_number or _extract_room_number(payload.query_text)
    missing: list[str] = []
    if class_date is None:
        missing.append("class_date")
    if start_time is None:
        missing.append("start_time")
    if end_time is None and start_time is not None:
        start_dt = datetime.combine(date.today(), start_time)
        end_dt = start_dt + timedelta(minutes=60)
        if end_dt.date() == start_dt.date():
            end_time = end_dt.time()
    if end_time is None:
        missing.append("end_time")
    if mode == "offline" and not room_number:
        missing.append("room_number")
    return class_date, start_time, end_time, mode, room_number, missing


def _remedial_plan_response(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[schemas.CopilotQueryResponse, dict[str, Any]]:
    if current_user.role not in {models.UserRole.ADMIN, models.UserRole.FACULTY}:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.DENIED,
                title="Remedial Planning Restricted",
                explanation=["Only admin and faculty accounts can create remedial plans."],
                next_steps=_supported_queries_for_role(current_user.role),
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    course, course_error = _resolve_remedial_course(payload, db=db, current_user=current_user)
    if course_error:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Blocked",
                explanation=[course_error],
                next_steps=["Retry with a valid course code or course id."],
            ),
            {"scope": f"role:{current_user.role.value}"},
        )
    if not course:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Blocked",
                explanation=["Course was not found."],
            ),
            {"scope": f"role:{current_user.role.value}"},
        )

    section, section_error = _resolve_target_section(payload, db=db, current_user=current_user)
    if section_error:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Blocked",
                explanation=[section_error],
                next_steps=["Retry with a valid in-scope section token."],
            ),
            {"scope": f"course:{int(course.id)}", "target_course_id": int(course.id)},
        )
    if not section:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Blocked",
                explanation=["Section was not resolved for the remedial scope."],
            ),
            {"scope": f"course:{int(course.id)}", "target_course_id": int(course.id)},
        )

    students = (
        db.query(models.Student)
        .join(models.Enrollment, models.Enrollment.student_id == models.Student.id)
        .filter(
            models.Enrollment.course_id == int(course.id),
            models.Student.section == section,
        )
        .order_by(models.Student.name.asc(), models.Student.id.asc())
        .all()
    )
    if not students:
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Blocked",
                explanation=[f"No enrolled students were found for section {section} in {course.code}."],
            ),
            {
                "scope": f"course:{int(course.id)}|section:{section}",
                "target_course_id": int(course.id),
                "target_section": section,
            },
        )

    student_ids = [int(student.id) for student in students]
    attendance_rows = (
        db.query(
            models.AttendanceRecord.student_id,
            func.count(models.AttendanceRecord.id).label("marked"),
            func.sum(
                case(
                    (models.AttendanceRecord.status == models.AttendanceStatus.PRESENT, 1),
                    else_=0,
                )
            ).label("present"),
        )
        .filter(
            models.AttendanceRecord.course_id == int(course.id),
            models.AttendanceRecord.student_id.in_(student_ids),
        )
        .group_by(models.AttendanceRecord.student_id)
        .all()
    )
    attendance_map = {
        int(student_id): {
            "marked": int(marked or 0),
            "present": int(present or 0),
        }
        for student_id, marked, present in attendance_rows
    }
    at_risk_names: list[str] = []
    watchlist_names: list[str] = []
    percents: list[float] = []
    for student in students:
        stats = attendance_map.get(int(student.id), {"marked": 0, "present": 0})
        marked_count = int(stats["marked"])
        present_count = int(stats["present"])
        percent = round((present_count / marked_count) * 100.0, 2) if marked_count else 0.0
        if marked_count:
            percents.append(percent)
        if marked_count >= 4 and percent < 75.0:
            at_risk_names.append(student.name)
        elif marked_count > 0 and percent < 80.0:
            watchlist_names.append(student.name)

    average_percent = round(sum(percents) / len(percents), 2) if percents else 0.0
    evidence = [
        _evidence("Course", f"{course.code} | {course.title}"),
        _evidence("Section", section),
        _evidence("Students in scope", str(len(students))),
        _evidence("At-risk students", str(len(at_risk_names)), "warning" if at_risk_names else "pass"),
        _evidence("Watchlist students", str(len(watchlist_names)), "warning" if watchlist_names else "pass"),
        _evidence("Average recorded attendance", f"{average_percent:.2f}%"),
    ]
    explanation = [
        f"Prepared a remedial recovery plan for {course.code} section {section}.",
        f"{len(students)} student(s) are in scope; {len(at_risk_names)} are already below the 75% threshold.",
        "Recommended 60-minute structure: 15 min recap, 20 min guided correction, 15 min targeted practice, 10 min exit check.",
    ]
    if at_risk_names:
        explanation.append("Priority students: " + ", ".join(at_risk_names[:6]) + ("." if len(at_risk_names) <= 6 else ", ..."))

    class_date, start_time, end_time, class_mode, room_number, missing = _resolve_remedial_schedule_inputs(payload)
    actions = [_action("prepare_remedial_scope", "completed", f"Scoped {len(students)} student(s)")]
    next_steps: list[str] = []
    entities: dict[str, Any] = {
        "course_id": int(course.id),
        "course_code": course.code,
        "section": section,
        "students_in_scope": len(students),
        "at_risk_students": len(at_risk_names),
    }

    if missing:
        actions.append(_action("schedule_makeup_class", "blocked", "Missing required scheduling fields"))
        next_steps.append(
            f"Retry with date and time, for example: Create a remedial plan for course {course.code} section {section} on 2026-03-10 at 15:00"
        )
        if class_mode == "offline":
            next_steps.append("Include a room number because offline remedial classes require room assignment.")
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Plan Prepared",
                explanation=explanation + [f"Execution is blocked until these fields are provided: {', '.join(missing)}."],
                evidence=evidence,
                actions=actions,
                next_steps=next_steps,
                entities=entities,
            ),
            {
                "scope": f"course:{int(course.id)}|section:{section}",
                "target_course_id": int(course.id),
                "target_section": section,
            },
        )

    faculty_id = int(current_user.faculty_id) if current_user.role == models.UserRole.FACULTY else int(course.faculty_id)
    topic = f"Attendance recovery | {course.code} | Section {section}"
    try:
        class_out = create_makeup_class(
            schemas.MakeUpClassCreate(
                course_id=int(course.id),
                faculty_id=faculty_id,
                class_date=class_date,
                start_time=start_time,
                end_time=end_time,
                topic=topic,
                sections=[section],
                class_mode=class_mode,
                room_number=room_number if class_mode == "offline" else None,
            ),
            db=db,
            current_user=current_user,
        )
    except HTTPException as exc:
        actions.append(_action("schedule_makeup_class", "failed", str(exc.detail)))
        return (
            schemas.CopilotQueryResponse(
                intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
                outcome=schemas.CopilotOutcome.BLOCKED,
                title="Remedial Scheduling Failed",
                explanation=explanation + [str(exc.detail)],
                evidence=evidence,
                actions=actions,
                next_steps=["Adjust the date, time, or section scope and retry."],
                entities=entities,
            ),
            {
                "scope": f"course:{int(course.id)}|section:{section}",
                "target_course_id": int(course.id),
                "target_section": section,
            },
        )

    actions.append(_action("schedule_makeup_class", "completed", f"Scheduled class {int(class_out.id)}"))
    explanation.append(
        f"Scheduled the remedial class for {class_out.class_date.isoformat()} {class_out.start_time.strftime('%H:%M')}-{class_out.end_time.strftime('%H:%M')} ({class_out.class_mode})."
    )
    entities.update(
        {
            "class_id": int(class_out.id),
            "remedial_code": class_out.remedial_code,
        }
    )

    if payload.send_message:
        try:
            send_out = send_remedial_code_to_sections(
                int(class_out.id),
                schemas.RemedialSendMessageRequest(custom_message=None),
                db=db,
                current_user=current_user,
            )
            actions.append(_action("send_remedial_code", "completed", send_out.message))
            explanation.append(f"Sent the remedial code to {int(send_out.recipients)} student(s).")
            entities["message_recipients"] = int(send_out.recipients)
        except HTTPException as exc:
            actions.append(_action("send_remedial_code", "failed", str(exc.detail)))
            explanation.append(f"Class was scheduled, but notification dispatch failed: {exc.detail}")
            next_steps.append("Open the Remedial module and resend the code manually if needed.")

    return (
        schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.CREATE_REMEDIAL_PLAN,
            outcome=schemas.CopilotOutcome.COMPLETED,
            title="Remedial Plan Scheduled",
            explanation=explanation,
            evidence=evidence,
            actions=actions,
            next_steps=next_steps or ["Track attendance from the Remedial module once the class starts."],
            entities=entities,
        ),
        {
            "scope": f"course:{int(course.id)}|section:{section}",
            "target_course_id": int(course.id),
            "target_section": section,
        },
    )


def _module_assist_response(
    payload: schemas.CopilotQueryRequest,
    *,
    db: Session,
    current_user: CurrentUser,
) -> tuple[schemas.CopilotQueryResponse, dict[str, Any]]:
    accessible_modules = _accessible_modules_for_role(current_user.role)
    if not accessible_modules:
        return _unsupported_response(current_user), {"scope": f"role:{current_user.role.value}"}

    mentioned_modules = _mentioned_modules_from_query(payload.query_text)
    requested_modules = [module for module in mentioned_modules if module in accessible_modules]
    denied_modules = [module for module in mentioned_modules if module not in accessible_modules]
    active_module = _normalize_module_key(payload.active_module)

    if mentioned_modules and not requested_modules:
        accessible_labels = ", ".join(_copilot_module_label(module) for module in accessible_modules)
        denied_labels = ", ".join(_copilot_module_label(module) for module in denied_modules)
        response = schemas.CopilotQueryResponse(
            intent=schemas.CopilotIntent.MODULE_ASSIST,
            outcome=schemas.CopilotOutcome.DENIED,
            title="Module Access Restricted",
            explanation=[
                f"Your role cannot access the requested module scope: {denied_labels}.",
                f"You can run Campus Copilot in these modules: {accessible_labels}.",
            ],
            next_steps=[
                "Switch to an accessible module and ask the same question again.",
                "If your role should include that module, request access policy update.",
            ],
            entities={
                "requested_modules": mentioned_modules,
                "denied_modules": denied_modules,
                "accessible_modules": accessible_modules,
            },
        )
        return response, {"scope": f"role:{current_user.role.value}|module_access:denied"}

    broad_scope_requested = _is_broad_module_summary_query(payload.query_text)
    if requested_modules:
        modules_to_answer = requested_modules
    elif broad_scope_requested or len(accessible_modules) == 1:
        modules_to_answer = list(accessible_modules)
    elif active_module and active_module in accessible_modules:
        modules_to_answer = [active_module]
    else:
        modules_to_answer = [accessible_modules[0]]
    module_labels = [_copilot_module_label(module) for module in modules_to_answer]
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    active_food_statuses = {
        models.FoodOrderStatus.PLACED.value,
        models.FoodOrderStatus.VERIFIED.value,
        models.FoodOrderStatus.PREPARING.value,
        models.FoodOrderStatus.OUT_FOR_DELIVERY.value,
        models.FoodOrderStatus.READY.value,
    }

    explanation: list[str] = []
    evidence: list[schemas.CopilotEvidenceItem] = []
    actions = [_action("module_scoped_answer", "completed", f"Answered {len(modules_to_answer)} module scope(s)")]
    next_steps: list[str] = []
    entities: dict[str, Any] = {
        "requested_modules": modules_to_answer,
        "mentioned_modules": mentioned_modules,
        "accessible_modules": accessible_modules,
        "active_module": active_module,
        "scope_mode": "broad" if broad_scope_requested else "focused",
    }
    client_context = _context_dict(payload.client_context)
    ui_context = _context_dict(client_context.get("ui"))
    if ui_context:
        entities["ui_context"] = ui_context
    if client_context:
        entities["client_context_modules"] = sorted(
            key for key, value in client_context.items() if isinstance(value, dict) and value
        )
    if active_module:
        active_module_context = _context_dict(client_context.get(active_module))
        if active_module_context:
            entities["active_module_context"] = active_module_context
    response_title = "Campus Copilot Module Assist"
    response_outcome = schemas.CopilotOutcome.COMPLETED
    skip_llm_rewrite = False

    if denied_modules:
        explanation.append(
            "Some requested modules were skipped due to role access: "
            + ", ".join(_copilot_module_label(module) for module in denied_modules)
            + "."
        )
        entities["denied_modules"] = denied_modules

    for module_key in modules_to_answer:
        if module_key == "attendance":
            if current_user.role == models.UserRole.STUDENT:
                if not current_user.student_id:
                    explanation.append("Attendance: student linkage is missing on your account.")
                    evidence.append(_evidence("Attendance scope", "Student link missing", "fail"))
                else:
                    aggregate = get_student_attendance_aggregate(db=db, current_user=current_user)
                    at_risk = [
                        row.course_code
                        for row in aggregate.courses
                        if row.delivered_classes >= 4 and row.attendance_percent < 75.0
                    ]
                    watchlist = [
                        row.course_code
                        for row in aggregate.courses
                        if row.delivered_classes > 0 and 75.0 <= row.attendance_percent < 80.0
                    ]
                    explanation.append(
                        f"Attendance: aggregate is {aggregate.aggregate_percent:.2f}% "
                        f"({aggregate.attended_total}/{aggregate.delivered_total}) across {len(aggregate.courses)} course(s)."
                    )
                    if at_risk:
                        explanation.append("Attendance risk (<75%): " + ", ".join(at_risk[:6]) + ("." if len(at_risk) <= 6 else ", ..."))
                    elif watchlist:
                        explanation.append("Attendance watchlist (75-79.99%): " + ", ".join(watchlist[:6]) + ("." if len(watchlist) <= 6 else ", ..."))
                    else:
                        explanation.append("Attendance status: no enrolled course is currently below 75%.")
                    evidence.append(
                        _evidence(
                            "Attendance aggregate",
                            f"{aggregate.aggregate_percent:.2f}% ({aggregate.attended_total}/{aggregate.delivered_total})",
                            "warning" if at_risk else "pass",
                        )
                    )
                    evidence.append(
                        _evidence(
                            "Courses at risk",
                            str(len(at_risk)),
                            "warning" if at_risk else "pass",
                        )
                    )
                    entities["attendance"] = {
                        "aggregate_percent": float(aggregate.aggregate_percent),
                        "at_risk_courses": at_risk,
                        "watchlist_courses": watchlist,
                    }
            elif current_user.role == models.UserRole.FACULTY:
                if not current_user.faculty_id:
                    explanation.append("Attendance: faculty linkage is missing on your account.")
                    evidence.append(_evidence("Attendance scope", "Faculty link missing", "fail"))
                else:
                    faculty_id = int(current_user.faculty_id)
                    taught_courses = int(
                        db.query(func.count(models.Course.id))
                        .filter(models.Course.faculty_id == faculty_id)
                        .scalar()
                        or 0
                    )
                    today_classes = int(
                        db.query(func.count(models.ClassSchedule.id))
                        .filter(
                            models.ClassSchedule.faculty_id == faculty_id,
                            models.ClassSchedule.weekday == int(today.weekday()),
                            models.ClassSchedule.is_active.is_(True),
                        )
                        .scalar()
                        or 0
                    )
                    pending_rectifications = int(
                        db.query(func.count(models.AttendanceRectificationRequest.id))
                        .filter(
                            models.AttendanceRectificationRequest.faculty_id == faculty_id,
                            models.AttendanceRectificationRequest.status == models.AttendanceRectificationStatus.PENDING,
                        )
                        .scalar()
                        or 0
                    )
                    explanation.append(
                        f"Attendance: you are mapped to {taught_courses} course(s), with {today_classes} active class slot(s) today "
                        f"and {pending_rectifications} pending rectification request(s)."
                    )
                    evidence.append(_evidence("Courses assigned", str(taught_courses)))
                    evidence.append(_evidence("Today's class slots", str(today_classes)))
                    evidence.append(
                        _evidence(
                            "Pending rectifications",
                            str(pending_rectifications),
                            "warning" if pending_rectifications else "pass",
                        )
                    )
                    entities["attendance"] = {
                        "courses_assigned": taught_courses,
                        "today_class_slots": today_classes,
                        "pending_rectifications": pending_rectifications,
                    }
            else:
                total_students = int(db.query(func.count(models.Student.id)).scalar() or 0)
                today_classes = int(
                    db.query(func.count(models.ClassSchedule.id))
                    .filter(
                        models.ClassSchedule.weekday == int(today.weekday()),
                        models.ClassSchedule.is_active.is_(True),
                    )
                    .scalar()
                    or 0
                )
                pending_rectifications = int(
                    db.query(func.count(models.AttendanceRectificationRequest.id))
                    .filter(models.AttendanceRectificationRequest.status == models.AttendanceRectificationStatus.PENDING)
                    .scalar()
                    or 0
                )
                pending_corrections = int(
                    db.query(func.count(models.RMSAttendanceCorrectionRequest.id))
                    .filter(
                        models.RMSAttendanceCorrectionRequest.status
                        == models.RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL
                    )
                    .scalar()
                    or 0
                )
                explanation.append(
                    "Attendance: campus view shows "
                    f"{today_classes} active class slot(s) today, {pending_rectifications} pending rectification request(s), "
                    f"{pending_corrections} pending correction approval request(s), and {total_students} student profile(s)."
                )
                evidence.append(_evidence("Total students", str(total_students)))
                evidence.append(_evidence("Today's class slots", str(today_classes)))
                evidence.append(
                    _evidence(
                        "Pending correction approvals",
                        str(pending_corrections),
                        "warning" if pending_corrections else "pass",
                    )
                )
                entities["attendance"] = {
                    "total_students": total_students,
                    "today_class_slots": today_classes,
                    "pending_rectifications": pending_rectifications,
                    "pending_correction_approvals": pending_corrections,
                }

        if module_key == "food":
            if current_user.role == models.UserRole.STUDENT and current_user.student_id:
                if len(modules_to_answer) == 1 and _looks_like_food_order_blocker_query(
                    payload.query_text,
                    active_module=active_module,
                ):
                    assessment = _student_food_order_blocker_assessment(
                        payload,
                        db=db,
                        current_user=current_user,
                        active_food_statuses=active_food_statuses,
                        today=today,
                    )
                    explanation.extend(assessment["explanation"])
                    evidence.extend(assessment["evidence"])
                    next_steps = list(assessment["next_steps"])
                    entities.update(assessment["entities"])
                    actions.append(assessment["action"])
                    response_title = str(assessment["title"] or response_title)
                    response_outcome = (
                        schemas.CopilotOutcome.BLOCKED
                        if assessment["blocked"]
                        else schemas.CopilotOutcome.COMPLETED
                    )
                    skip_llm_rewrite = True
                    continue
                student_id = int(current_user.student_id)
                status_rows = (
                    db.query(models.FoodOrder.status, func.count(models.FoodOrder.id))
                    .filter(
                        models.FoodOrder.student_id == student_id,
                        models.FoodOrder.order_date >= (today - timedelta(days=7)),
                    )
                    .group_by(models.FoodOrder.status)
                    .all()
                )
                status_map = {
                    str(status.value if isinstance(status, models.FoodOrderStatus) else status): int(count or 0)
                    for status, count in status_rows
                }
                active_count = sum(count for key, count in status_map.items() if key in active_food_statuses)
                delivered_count = int(status_map.get(models.FoodOrderStatus.DELIVERED.value, 0))
                collected_count = int(status_map.get(models.FoodOrderStatus.COLLECTED.value, 0))
                latest_order = (
                    db.query(models.FoodOrder)
                    .filter(models.FoodOrder.student_id == student_id)
                    .order_by(models.FoodOrder.created_at.desc(), models.FoodOrder.id.desc())
                    .first()
                )
                explanation.append(
                    "Food Hall: "
                    f"{active_count} active order(s), {delivered_count + collected_count} fulfilled order(s) in the last 7 days."
                )
                if latest_order is not None:
                    explanation.append(
                        f"Latest order status is {latest_order.status.value} for {latest_order.order_date.isoformat()}."
                    )
                evidence.append(_evidence("Food active orders (7d)", str(active_count), "warning" if active_count else "pass"))
                entities["food"] = {
                    "active_orders_7d": active_count,
                    "fulfilled_orders_7d": delivered_count + collected_count,
                    "latest_status": latest_order.status.value if latest_order is not None else None,
                }
            else:
                owner_shop_ids: list[int] = []
                if current_user.role == models.UserRole.OWNER:
                    owner_shop_ids = [
                        int(row.id)
                        for row in db.query(models.FoodShop.id)
                        .filter(models.FoodShop.owner_user_id == int(current_user.id))
                        .all()
                    ]
                    if not owner_shop_ids:
                        explanation.append("Food Hall: no food shops are linked to your owner account yet.")
                        evidence.append(_evidence("Owned food shops", "0", "warning"))
                        entities["food"] = {"owned_shop_count": 0}
                        continue
                order_query = db.query(models.FoodOrder).filter(models.FoodOrder.order_date == today)
                if owner_shop_ids:
                    order_query = order_query.filter(models.FoodOrder.shop_id.in_(owner_shop_ids))
                today_orders = int(order_query.count())
                active_orders = int(
                    order_query
                    .filter(models.FoodOrder.status.in_([models.FoodOrderStatus(value) for value in active_food_statuses]))
                    .count()
                )
                fulfilled_orders = int(
                    order_query
                    .filter(
                        models.FoodOrder.status.in_(
                            [models.FoodOrderStatus.DELIVERED, models.FoodOrderStatus.COLLECTED]
                        )
                    )
                    .count()
                )
                if current_user.role == models.UserRole.OWNER:
                    explanation.append(
                        f"Food Hall: your shop scope has {today_orders} order(s) today, with "
                        f"{active_orders} active and {fulfilled_orders} fulfilled."
                    )
                    evidence.append(_evidence("Owned food shops", str(len(owner_shop_ids))))
                else:
                    explanation.append(
                        f"Food Hall: campus flow has {today_orders} order(s) today, "
                        f"{active_orders} active and {fulfilled_orders} fulfilled."
                    )
                evidence.append(_evidence("Today's food orders", str(today_orders)))
                evidence.append(_evidence("Active food orders", str(active_orders), "warning" if active_orders else "pass"))
                entities["food"] = {
                    "today_orders": today_orders,
                    "active_orders": active_orders,
                    "fulfilled_orders": fulfilled_orders,
                    "owner_shop_count": len(owner_shop_ids) if owner_shop_ids else None,
                }

        if module_key == "saarthi" and current_user.role == models.UserRole.STUDENT:
            if not current_user.student_id:
                explanation.append("Saarthi: student linkage is missing on your account.")
                evidence.append(_evidence("Saarthi scope", "Student link missing", "fail"))
            else:
                student_id = int(current_user.student_id)
                session = (
                    db.query(models.SaarthiSession)
                    .filter(
                        models.SaarthiSession.student_id == student_id,
                        models.SaarthiSession.week_start_date == week_start,
                    )
                    .first()
                )
                if session is None:
                    explanation.append("Saarthi: no session record exists yet for this week.")
                    evidence.append(_evidence("Saarthi weekly session", "Not started", "warning"))
                    entities["saarthi"] = {"week_started": False}
                else:
                    message_count = int(
                        db.query(func.count(models.SaarthiMessage.id))
                        .filter(models.SaarthiMessage.session_id == int(session.id))
                        .scalar()
                        or 0
                    )
                    credited = bool(session.attendance_marked_at)
                    explanation.append(
                        "Saarthi: "
                        f"{message_count} message(s) this week; attendance credit is "
                        f"{'secured' if credited else 'pending Sunday check-in'}."
                    )
                    evidence.append(_evidence("Saarthi weekly messages", str(message_count)))
                    evidence.append(
                        _evidence(
                            "Saarthi attendance credit",
                            "Credited" if credited else "Pending",
                            "pass" if credited else "warning",
                        )
                    )
                    entities["saarthi"] = {
                        "week_started": True,
                        "message_count": message_count,
                        "attendance_credited": credited,
                        "mandatory_date": session.mandatory_date.isoformat(),
                    }

        if module_key == "remedial":
            if current_user.role == models.UserRole.STUDENT:
                if not current_user.student_id:
                    explanation.append("Remedial: student linkage is missing on your account.")
                    evidence.append(_evidence("Remedial scope", "Student link missing", "fail"))
                else:
                    student = db.get(models.Student, int(current_user.student_id))
                    course_ids = [
                        int(row.course_id)
                        for row in db.query(models.Enrollment.course_id)
                        .filter(models.Enrollment.student_id == int(current_user.student_id))
                        .all()
                    ]
                    if not course_ids:
                        explanation.append("Remedial: no enrolled courses were found for remedial scheduling scope.")
                        evidence.append(_evidence("Remedial enrolled courses", "0", "warning"))
                        entities["remedial"] = {"upcoming_classes": 0}
                    else:
                        base_query = (
                            db.query(models.MakeUpClass)
                            .filter(
                                models.MakeUpClass.course_id.in_(course_ids),
                                models.MakeUpClass.class_date >= today,
                                models.MakeUpClass.is_active.is_(True),
                            )
                        )
                        student_section = _student_section_token(student)
                        if student_section:
                            base_query = base_query.filter(
                                models.MakeUpClass.sections_json.like(f'%"{student_section}"%')
                            )
                        upcoming_count = int(base_query.count())
                        next_class = (
                            base_query.order_by(models.MakeUpClass.class_date.asc(), models.MakeUpClass.start_time.asc()).first()
                        )
                        explanation.append(f"Remedial: {upcoming_count} upcoming active remedial class(es) in your current scope.")
                        if next_class is not None:
                            explanation.append(
                                f"Next remedial class is on {next_class.class_date.isoformat()} at {next_class.start_time.strftime('%H:%M')}."
                            )
                        evidence.append(
                            _evidence(
                                "Upcoming remedial classes",
                                str(upcoming_count),
                                "warning" if upcoming_count else "pass",
                            )
                        )
                        entities["remedial"] = {
                            "upcoming_classes": upcoming_count,
                            "next_class_id": int(next_class.id) if next_class is not None else None,
                        }
            elif current_user.role == models.UserRole.FACULTY:
                if not current_user.faculty_id:
                    explanation.append("Remedial: faculty linkage is missing on your account.")
                    evidence.append(_evidence("Remedial scope", "Faculty link missing", "fail"))
                else:
                    faculty_id = int(current_user.faculty_id)
                    base_query = (
                        db.query(models.MakeUpClass)
                        .filter(
                            models.MakeUpClass.faculty_id == faculty_id,
                            models.MakeUpClass.class_date >= today,
                            models.MakeUpClass.is_active.is_(True),
                        )
                    )
                    upcoming_count = int(base_query.count())
                    next_class = base_query.order_by(models.MakeUpClass.class_date.asc(), models.MakeUpClass.start_time.asc()).first()
                    explanation.append(f"Remedial: you have {upcoming_count} upcoming active remedial class(es).")
                    if next_class is not None:
                        explanation.append(
                            f"Next remedial class is on {next_class.class_date.isoformat()} at {next_class.start_time.strftime('%H:%M')}."
                        )
                    evidence.append(_evidence("Upcoming remedial classes", str(upcoming_count)))
                    entities["remedial"] = {
                        "upcoming_classes": upcoming_count,
                        "next_class_id": int(next_class.id) if next_class is not None else None,
                    }

        if module_key == "rms":
            if current_user.role == models.UserRole.FACULTY:
                if not current_user.faculty_id:
                    explanation.append("RMS: faculty linkage is missing on your account.")
                    evidence.append(_evidence("RMS scope", "Faculty link missing", "fail"))
                else:
                    faculty_id = int(current_user.faculty_id)
                    faculty = db.get(models.Faculty, faculty_id)
                    section_scope = sorted(remedial_faculty_allowed_sections(faculty))
                    case_query = db.query(models.RMSCase).filter(models.RMSCase.status != models.RMSCaseStatus.CLOSED)
                    if section_scope:
                        case_query = case_query.filter(models.RMSCase.section.in_(section_scope))
                    else:
                        case_query = case_query.filter(models.RMSCase.faculty_id == faculty_id)
                    open_cases = int(case_query.count())
                    escalated_cases = int(case_query.filter(models.RMSCase.is_escalated.is_(True)).count())
                    pending_corrections = int(
                        db.query(func.count(models.RMSAttendanceCorrectionRequest.id))
                        .filter(
                            models.RMSAttendanceCorrectionRequest.faculty_id == faculty_id,
                            models.RMSAttendanceCorrectionRequest.status
                            == models.RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL,
                        )
                        .scalar()
                        or 0
                    )
                    explanation.append(
                        f"RMS: {open_cases} open case(s), {escalated_cases} escalated, and "
                        f"{pending_corrections} pending attendance correction request(s) in your scope."
                    )
                    evidence.append(_evidence("Open RMS cases", str(open_cases), "warning" if open_cases else "pass"))
                    evidence.append(
                        _evidence(
                            "Escalated RMS cases",
                            str(escalated_cases),
                            "fail" if escalated_cases else "pass",
                        )
                    )
                    entities["rms"] = {
                        "open_cases": open_cases,
                        "escalated_cases": escalated_cases,
                        "pending_corrections": pending_corrections,
                        "section_scope": section_scope,
                    }
            else:
                open_cases = int(
                    db.query(func.count(models.RMSCase.id))
                    .filter(models.RMSCase.status != models.RMSCaseStatus.CLOSED)
                    .scalar()
                    or 0
                )
                escalated_cases = int(
                    db.query(func.count(models.RMSCase.id))
                    .filter(
                        models.RMSCase.status != models.RMSCaseStatus.CLOSED,
                        models.RMSCase.is_escalated.is_(True),
                    )
                    .scalar()
                    or 0
                )
                pending_corrections = int(
                    db.query(func.count(models.RMSAttendanceCorrectionRequest.id))
                    .filter(
                        models.RMSAttendanceCorrectionRequest.status
                        == models.RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL
                    )
                    .scalar()
                    or 0
                )
                explanation.append(
                    f"RMS: campus queue has {open_cases} open case(s), {escalated_cases} escalated, and "
                    f"{pending_corrections} pending attendance correction approval request(s)."
                )
                evidence.append(_evidence("Open RMS cases", str(open_cases), "warning" if open_cases else "pass"))
                evidence.append(
                    _evidence(
                        "Escalated RMS cases",
                        str(escalated_cases),
                        "fail" if escalated_cases else "pass",
                    )
                )
                entities["rms"] = {
                    "open_cases": open_cases,
                    "escalated_cases": escalated_cases,
                    "pending_correction_approvals": pending_corrections,
                }

        if module_key == "administrative":
            copilot_runs_today = int(
                db.query(func.count(models.CopilotAuditLog.id))
                .filter(models.CopilotAuditLog.created_at >= datetime.combine(today, time.min))
                .scalar()
                or 0
            )
            pending_corrections = int(
                db.query(func.count(models.RMSAttendanceCorrectionRequest.id))
                .filter(
                    models.RMSAttendanceCorrectionRequest.status
                    == models.RMSAttendanceCorrectionStatus.PENDING_ADMIN_APPROVAL
                )
                .scalar()
                or 0
            )
            pending_identity_reviews = int(
                db.query(func.count(models.IdentityVerificationCase.id))
                .filter(
                    models.IdentityVerificationCase.status.in_(
                        [
                            models.IdentityVerificationStatus.PENDING,
                            models.IdentityVerificationStatus.IN_REVIEW,
                        ]
                    )
                )
                .scalar()
                or 0
            )
            flagged_identity_cases = int(
                db.query(func.count(models.IdentityVerificationCase.id))
                .filter(models.IdentityVerificationCase.status == models.IdentityVerificationStatus.FLAGGED)
                .scalar()
                or 0
            )
            explanation.append(
                f"Administrative: {copilot_runs_today} copilot audit run(s) today, "
                f"{pending_corrections} pending correction approval(s), "
                f"{pending_identity_reviews} pending identity review(s), and "
                f"{flagged_identity_cases} flagged identity case(s)."
            )
            evidence.append(_evidence("Copilot runs today", str(copilot_runs_today)))
            evidence.append(
                _evidence(
                    "Pending identity reviews",
                    str(pending_identity_reviews),
                    "warning" if pending_identity_reviews else "pass",
                )
            )
            entities["administrative"] = {
                "copilot_runs_today": copilot_runs_today,
                "pending_correction_approvals": pending_corrections,
                "pending_identity_reviews": pending_identity_reviews,
                "flagged_identity_cases": flagged_identity_cases,
            }

    llm_structured = None
    if not skip_llm_rewrite:
        try:
            llm_structured = generate_structured_copilot_answer(
                query_text=payload.query_text,
                role=current_user.role.value,
                module_labels=module_labels,
                denied_labels=[_copilot_module_label(module) for module in denied_modules],
                explanation=explanation,
                evidence=[
                    {
                        "label": str(item.label),
                        "value": str(item.value),
                        "status": str(item.status),
                    }
                    for item in evidence
                ],
                next_steps=next_steps,
                entities=entities,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "copilot_llm_rewrite_failed user_id=%s role=%s modules=%s",
                current_user.id,
                current_user.role.value,
                ",".join(modules_to_answer),
            )
            llm_structured = None

    title = response_title
    if isinstance(llm_structured, dict):
        llm_title = str(llm_structured.get("title") or "").strip()
        llm_explanation = llm_structured.get("explanation")
        llm_next_steps = llm_structured.get("next_steps")
        if llm_title:
            title = llm_title
        if isinstance(llm_explanation, list) and llm_explanation:
            explanation = [str(item) for item in llm_explanation if str(item or "").strip()]
        if isinstance(llm_next_steps, list) and llm_next_steps:
            next_steps = [str(item) for item in llm_next_steps if str(item or "").strip()]
    if not next_steps:
        if broad_scope_requested:
            next_steps = ["Ask a module-specific follow-up with course code, section, or student id for precise actions."]
        elif len(modules_to_answer) == 1:
            next_steps = _focused_module_assist_next_steps(
                modules_to_answer[0],
                role=current_user.role,
            )
        else:
            next_steps = [
                "Stay inside the relevant module and retry the exact in-app step tied to your question.",
                "If you switch modules, ask again from that module so Campus Copilot can use the active screen context.",
            ]

    response = schemas.CopilotQueryResponse(
        intent=schemas.CopilotIntent.MODULE_ASSIST,
        outcome=response_outcome,
        title=title,
        explanation=explanation,
        evidence=evidence,
        actions=actions,
        next_steps=next_steps,
        entities=entities,
    )
    return response, {"scope": f"role:{current_user.role.value}|modules:{','.join(modules_to_answer)}"}


@router.post("/query", response_model=schemas.CopilotQueryResponse)
def copilot_query(
    payload: schemas.CopilotQueryRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(
            models.UserRole.ADMIN,
            models.UserRole.FACULTY,
            models.UserRole.STUDENT,
            models.UserRole.OWNER,
        )
    ),
):
    if _looks_like_sensitive_data_request(payload.query_text):
        response = _sensitive_request_denied_response(current_user)
        return _persist_audit(
            db,
            current_user=current_user,
            payload=payload,
            response=response,
            scope=f"role:{current_user.role.value}|security:sensitive_request",
        )
    intent = _resolve_intent(payload.query_text)
    handler_map = {
        schemas.CopilotIntent.ATTENDANCE_BLOCKER: _attendance_blocker_response,
        schemas.CopilotIntent.ELIGIBILITY_RISK: _eligibility_risk_response,
        schemas.CopilotIntent.CREATE_REMEDIAL_PLAN: _remedial_plan_response,
        schemas.CopilotIntent.STUDENT_FLAG_REASON: _flag_reason_response,
        schemas.CopilotIntent.MODULE_ASSIST: _module_assist_response,
        schemas.CopilotIntent.UNSUPPORTED: lambda payload, db, current_user: (
            _unsupported_response(current_user),
            {"scope": f"role:{current_user.role.value}"},
        ),
    }
    handler = handler_map[intent]
    try:
        response, audit_meta = handler(payload, db=db, current_user=current_user)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        logger.exception(
            "copilot_handler_failed user_id=%s role=%s intent=%s",
            current_user.id,
            current_user.role.value,
            intent.value,
        )
        response = schemas.CopilotQueryResponse(
            intent=intent,
            outcome=schemas.CopilotOutcome.FAILED,
            title="Campus Copilot Temporary Failure",
            explanation=[
                "Campus Copilot hit an internal processing error while preparing this response.",
                "Your request was not dropped; retry in a few seconds.",
            ],
            actions=[_action("copilot_query", "failed", "Internal handler exception")],
            next_steps=[
                "Retry the same question.",
                "If this repeats, ask admin to verify SQL auth-user sync for audit logging.",
            ],
        )
        audit_meta = {"scope": f"role:{current_user.role.value}|handler_error"}
    return _persist_audit(
        db,
        current_user=current_user,
        payload=payload,
        response=response,
        scope=audit_meta.get("scope"),
        target_student_id=audit_meta.get("target_student_id"),
        target_course_id=audit_meta.get("target_course_id"),
        target_section=audit_meta.get("target_section"),
    )


@router.get("/audit", response_model=list[schemas.CopilotAuditLogOut])
def list_copilot_audit(
    limit: int = Query(default=50, ge=1, le=200),
    actor_user_id: int | None = Query(default=None, ge=1),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    intent: schemas.CopilotIntent | None = Query(default=None),
    outcome: schemas.CopilotOutcome | None = Query(default=None),
    actor_role: models.UserRole | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(
            models.UserRole.ADMIN,
            models.UserRole.FACULTY,
            models.UserRole.STUDENT,
            models.UserRole.OWNER,
        )
    ),
):
    query = db.query(models.CopilotAuditLog, models.AuthUser.email).outerjoin(
        models.AuthUser,
        models.AuthUser.id == models.CopilotAuditLog.actor_user_id,
    )
    if current_user.role != models.UserRole.ADMIN:
        query = query.filter(models.CopilotAuditLog.actor_user_id == int(current_user.id))
    elif actor_user_id is not None:
        query = query.filter(models.CopilotAuditLog.actor_user_id == int(actor_user_id))

    if intent is not None:
        query = query.filter(models.CopilotAuditLog.intent == intent.value)
    if outcome is not None:
        query = query.filter(models.CopilotAuditLog.outcome == outcome.value)
    if actor_role is not None:
        query = query.filter(models.CopilotAuditLog.actor_role == actor_role.value)
    if q is not None:
        search_text = str(q).strip().lower()
        if search_text:
            pattern = f"%{search_text}%"
            filters = [
                func.lower(models.CopilotAuditLog.query_text).like(pattern),
                func.lower(func.coalesce(models.CopilotAuditLog.scope, "")).like(pattern),
                func.lower(func.coalesce(models.CopilotAuditLog.target_section, "")).like(pattern),
                func.lower(models.CopilotAuditLog.actor_role).like(pattern),
                func.lower(models.CopilotAuditLog.intent).like(pattern),
                func.lower(models.CopilotAuditLog.outcome).like(pattern),
                func.lower(func.coalesce(models.AuthUser.email, "")).like(pattern),
            ]
            if search_text.isdigit():
                numeric_id = int(search_text)
                filters.extend(
                    [
                        models.CopilotAuditLog.id == numeric_id,
                        models.CopilotAuditLog.actor_user_id == numeric_id,
                        models.CopilotAuditLog.target_student_id == numeric_id,
                        models.CopilotAuditLog.target_course_id == numeric_id,
                    ]
                )
            query = query.filter(or_(*filters))

    rows = (
        query.order_by(models.CopilotAuditLog.created_at.desc(), models.CopilotAuditLog.id.desc())
        .limit(int(limit))
        .all()
    )
    return [
        _serialize_audit_row(row, actor_email=actor_email)
        for row, actor_email in rows
    ]
