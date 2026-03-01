import hashlib
import hmac
import json
import math
import os
import re
import secrets
import razorpay
from datetime import date, datetime, timedelta
from datetime import time as dt_time
from threading import Lock
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pymongo.errors import DuplicateKeyError
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import CurrentUser, require_roles
from ..database import get_db
from ..food_bootstrap import bootstrap_food_hall_catalog
from ..mongo import get_mongo_db, mirror_document, mirror_event

router = APIRouter(prefix="/food", tags=["Food Pre-Ordering"])

_order_rate_lock = Lock()
_order_rate_buckets: dict[int, list[datetime]] = {}
_FOOD_SERVICE_START = dt_time(10, 0)
_FOOD_SERVICE_END = dt_time(21, 0)


def _float_env(name: str, default: float) -> float:
    raw = str(os.getenv(name, str(default))).strip()
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _int_env(name: str, default: int) -> int:
    raw = str(os.getenv(name, str(default))).strip()
    try:
        return int(raw)
    except ValueError:
        return int(default)


def _lpu_center_latitude() -> float:
    return _float_env("LPU_GEOFENCE_CENTER_LAT", 31.2536)


def _lpu_center_longitude() -> float:
    return _float_env("LPU_GEOFENCE_CENTER_LON", 75.7064)


def _lpu_radius_meters() -> float:
    return max(200.0, _float_env("LPU_GEOFENCE_RADIUS_M", 2500.0))


def _max_location_accuracy_m() -> float:
    return max(20.0, _float_env("LPU_GEOFENCE_MAX_ACCURACY_M", 180.0))


def _order_cancel_window_minutes() -> int:
    return max(2, min(60, _int_env("FOOD_ORDER_CANCEL_WINDOW_MIN", 10)))


def _order_timeout_minutes() -> int:
    return max(5, min(120, _int_env("FOOD_ORDER_TIMEOUT_MIN", 25)))


def _rate_limit_window_seconds() -> int:
    return max(10, min(300, _int_env("FOOD_ORDER_RATE_LIMIT_WINDOW_SEC", 60)))


def _rate_limit_max_orders() -> int:
    return max(2, min(40, _int_env("FOOD_ORDER_RATE_LIMIT_MAX", 12)))


def _delivery_fee_inr() -> float:
    return max(0.0, _float_env("FOOD_DELIVERY_FEE_INR", 30.0))


def _platform_fee_inr() -> float:
    return max(0.0, _float_env("FOOD_PLATFORM_FEE_INR", 5.0))


def _payment_webhook_token() -> str:
    return str(os.getenv("FOOD_PAYMENT_WEBHOOK_TOKEN", "")).strip()


def _razorpay_webhook_secret() -> str:
    return str(os.getenv("RAZORPAY_WEBHOOK_SECRET", "")).strip()


def _get_razorpay_client():
    key_id = os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    if key_id and key_secret:
        return razorpay.Client(auth=(key_id, key_secret))
    return None


def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    return 2.0 * earth_radius_m * math.asin(min(1.0, math.sqrt(a)))


def _evaluate_location_gate(
    *,
    latitude: float,
    longitude: float,
    accuracy_m: float | None,
) -> tuple[bool, str, float]:
    center_lat = _lpu_center_latitude()
    center_lon = _lpu_center_longitude()
    radius_m = _lpu_radius_meters()
    max_accuracy_m = _max_location_accuracy_m()
    distance_m = _haversine_distance_m(latitude, longitude, center_lat, center_lon)

    if accuracy_m is not None and accuracy_m > max_accuracy_m:
        return (
            False,
            f"Location accuracy is too low ({accuracy_m:.0f} m). Enable precise GPS and retry.",
            distance_m,
        )

    if distance_m > radius_m:
        return (
            False,
            f"Delivery is available only inside LPU campus. You are ~{distance_m:.0f} m from allowed zone.",
            distance_m,
        )

    return (
        True,
        f"Campus location verified ({distance_m:.0f} m from LPU center).",
        distance_m,
    )


def _serialize_json(raw_value: str | None) -> list[dict]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def _mongo_db_or_503():
    try:
        return get_mongo_db(required=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _mongo_read_preferred() -> bool:
    raw = (os.getenv("MONGO_READ_PREFERRED", "true") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _coerce_mongo_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _coerce_mongo_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    dt_value = _coerce_mongo_datetime(value)
    if dt_value is not None:
        return dt_value.date()
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _mongo_order_to_schema(doc: dict[str, Any]) -> schemas.FoodOrderOut | None:
    order_id_raw = doc.get("order_id", doc.get("id"))
    student_id_raw = doc.get("student_id")
    food_item_id_raw = doc.get("food_item_id")
    slot_id_raw = doc.get("slot_id")
    order_date = _coerce_mongo_date(doc.get("order_date"))
    if order_id_raw is None or student_id_raw is None or food_item_id_raw is None or slot_id_raw is None or not order_date:
        return None

    status_raw = str(doc.get("status") or models.FoodOrderStatus.PLACED.value).strip().lower()
    try:
        status_value = models.FoodOrderStatus(status_raw)
    except ValueError:
        status_value = models.FoodOrderStatus.PLACED

    return schemas.FoodOrderOut(
        id=int(order_id_raw),
        student_id=int(student_id_raw),
        shop_id=(int(doc["shop_id"]) if doc.get("shop_id") is not None else None),
        menu_item_id=(int(doc["menu_item_id"]) if doc.get("menu_item_id") is not None else None),
        food_item_id=int(food_item_id_raw),
        slot_id=int(slot_id_raw),
        order_date=order_date,
        quantity=int(doc.get("quantity") or 1),
        unit_price=float(doc.get("unit_price") or 0.0),
        total_price=float(doc.get("total_price") or 0.0),
        status=status_value,
        shop_name=(str(doc.get("shop_name")).strip() if doc.get("shop_name") else None),
        shop_block=(str(doc.get("shop_block")).strip() if doc.get("shop_block") else None),
        idempotency_key=(str(doc.get("idempotency_key")).strip() if doc.get("idempotency_key") else None),
        payment_status=str(doc.get("payment_status") or "pending"),
        payment_provider=(str(doc.get("payment_provider")).strip() if doc.get("payment_provider") else None),
        payment_reference=(str(doc.get("payment_reference")).strip() if doc.get("payment_reference") else None),
        status_note=(str(doc.get("status_note")).strip() if doc.get("status_note") else None),
        assigned_runner=(str(doc.get("assigned_runner")).strip() if doc.get("assigned_runner") else None),
        pickup_point=(str(doc.get("pickup_point")).strip() if doc.get("pickup_point") else None),
        delivery_eta_minutes=(int(doc["delivery_eta_minutes"]) if doc.get("delivery_eta_minutes") is not None else None),
        estimated_ready_at=_coerce_mongo_datetime(doc.get("estimated_ready_at")),
        location_verified=bool(doc.get("location_verified")),
        location_latitude=(float(doc["location_latitude"]) if doc.get("location_latitude") is not None else None),
        location_longitude=(float(doc["location_longitude"]) if doc.get("location_longitude") is not None else None),
        location_accuracy_m=(float(doc["location_accuracy_m"]) if doc.get("location_accuracy_m") is not None else None),
        last_location_verified_at=_coerce_mongo_datetime(doc.get("last_location_verified_at")),
        verified_at=_coerce_mongo_datetime(doc.get("verified_at")),
        preparing_at=_coerce_mongo_datetime(doc.get("preparing_at")),
        out_for_delivery_at=_coerce_mongo_datetime(doc.get("out_for_delivery_at")),
        delivered_at=_coerce_mongo_datetime(doc.get("delivered_at")),
        cancelled_at=_coerce_mongo_datetime(doc.get("cancelled_at")),
        cancel_reason=(str(doc.get("cancel_reason")).strip() if doc.get("cancel_reason") else None),
        rating_stars=(int(doc["rating_stars"]) if doc.get("rating_stars") is not None else None),
        rating_comment=(str(doc.get("rating_comment")).strip() if doc.get("rating_comment") else None),
        rated_at=_coerce_mongo_datetime(doc.get("rated_at")),
        rating_locked_at=_coerce_mongo_datetime(doc.get("rating_locked_at")),
        last_status_updated_at=_coerce_mongo_datetime(doc.get("last_status_updated_at")),
    )


def _list_orders_from_mongo(
    *,
    order_date: date | None,
    limit: int | None,
    current_user: CurrentUser,
):
    if not _mongo_read_preferred():
        return None
    mongo_db = get_mongo_db(required=False)
    if mongo_db is None:
        return None

    if current_user.role == models.UserRole.FACULTY:
        return []

    query_filter: dict[str, Any] = {}
    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly")
        query_filter["student_id"] = int(current_user.student_id)
    elif current_user.role == models.UserRole.OWNER:
        shop_docs = list(
            mongo_db["food_shops"].find(
                {"owner_user_id": int(current_user.id)},
                {"shop_id": 1, "id": 1},
            )
        )
        shop_ids = sorted(
            {
                int(doc.get("shop_id") or doc.get("id"))
                for doc in shop_docs
                if doc.get("shop_id") is not None or doc.get("id") is not None
            }
        )
        if not shop_ids:
            return []
        query_filter["shop_id"] = {"$in": shop_ids}

    if order_date:
        query_filter["order_date"] = {"$in": [order_date.isoformat(), order_date]}

    cursor = mongo_db["food_orders"].find(query_filter).sort([("created_at", -1), ("order_id", -1)])
    if limit:
        cursor = cursor.limit(int(limit))
    docs = list(cursor)

    rows: list[schemas.FoodOrderOut] = []
    for doc in docs:
        parsed = _mongo_order_to_schema(doc)
        if parsed is not None:
            rows.append(parsed)
    return rows


def _validate_order_time_window(*, order_date: date, slot: models.BreakSlot) -> None:
    if slot.start_time < _FOOD_SERVICE_START or slot.end_time > _FOOD_SERVICE_END:
        raise HTTPException(status_code=409, detail="Selected slot is not open for pickup.")

    today_local = date.today()
    if order_date != today_local:
        raise HTTPException(
            status_code=409,
            detail=f"Orders can be placed only for today ({today_local.isoformat()}).",
        )

    now_local = datetime.now()
    current_time = now_local.time()
    if current_time < _FOOD_SERVICE_START or current_time >= _FOOD_SERVICE_END:
        raise HTTPException(
            status_code=409,
            detail="Food hall is closed now. Ordering is open from 10:00 AM to 9:00 PM.",
        )

    if slot.end_time <= current_time:
        raise HTTPException(
            status_code=409,
            detail="Selected slot has already ended. Choose an upcoming slot.",
        )


def _require_student_id(current_user: CurrentUser) -> int:
    if current_user.role != models.UserRole.STUDENT or not current_user.student_id:
        raise HTTPException(status_code=403, detail="Food cart is available only for student accounts")
    return int(current_user.student_id)


def _normalize_food_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _build_cart_key(menu_item_id: int, item_note: str | None) -> str:
    return f"{int(menu_item_id)}::{_normalize_food_key(item_note)}"


def _empty_food_cart(student_id: int) -> schemas.FoodCartOut:
    return schemas.FoodCartOut(
        student_id=student_id,
        shop_id=None,
        items=[],
        total_items=0,
        total_quantity=0,
        total_price=0.0,
        checkout_preview_open=False,
        checkout_delivery_point=None,
        updated_at=datetime.utcnow(),
    )


def _cart_item_to_out(raw: dict[str, Any], default_shop_id: int | None = None) -> schemas.FoodCartItemOut | None:
    try:
        menu_item_id = int(raw.get("menu_item_id"))
    except (TypeError, ValueError):
        return None
    if menu_item_id <= 0:
        return None

    try:
        quantity = int(raw.get("quantity", 0))
    except (TypeError, ValueError):
        quantity = 0
    if quantity <= 0:
        return None

    try:
        shop_id = int(raw.get("shop_id") or default_shop_id or 0)
    except (TypeError, ValueError):
        shop_id = 0
    if shop_id <= 0:
        return None

    food_item_id_raw = raw.get("food_item_id")
    food_item_id: int | None
    try:
        food_item_id = int(food_item_id_raw) if food_item_id_raw is not None else None
    except (TypeError, ValueError):
        food_item_id = None
    if food_item_id is not None and food_item_id <= 0:
        food_item_id = None

    try:
        price_value = round(float(raw.get("price", 0.0)), 2)
    except (TypeError, ValueError):
        price_value = 0.0
    if price_value < 0:
        price_value = 0.0

    item_note = str(raw.get("item_note") or "").strip()[:240]
    cart_key = str(raw.get("cart_key") or "").strip() or _build_cart_key(menu_item_id, item_note)

    return schemas.FoodCartItemOut(
        cart_key=cart_key,
        shop_id=shop_id,
        menu_item_id=menu_item_id,
        food_item_id=food_item_id,
        name=str(raw.get("name") or "").strip()[:180] or f"Item #{menu_item_id}",
        price=price_value,
        quantity=quantity,
        item_note=item_note,
    )


def _food_cart_to_out(doc: dict[str, Any] | None, *, student_id: int) -> schemas.FoodCartOut:
    if not doc:
        return _empty_food_cart(student_id)

    cart_items: list[schemas.FoodCartItemOut] = []
    raw_items = doc.get("items") if isinstance(doc.get("items"), list) else []
    raw_shop_id = doc.get("shop_id")
    try:
        default_shop_id = int(raw_shop_id) if raw_shop_id is not None else None
    except (TypeError, ValueError):
        default_shop_id = None

    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        parsed = _cart_item_to_out(raw, default_shop_id=default_shop_id)
        if parsed:
            cart_items.append(parsed)

    if cart_items:
        resolved_shop_id = cart_items[0].shop_id
    else:
        resolved_shop_id = None

    total_quantity = sum(item.quantity for item in cart_items)
    total_price = round(sum(item.quantity * item.price for item in cart_items), 2)
    delivery_point = str(doc.get("checkout_delivery_point") or "").strip() or None
    checkout_preview_open = bool(doc.get("checkout_preview_open")) and bool(cart_items)
    updated_at = doc.get("updated_at")
    if not isinstance(updated_at, datetime):
        updated_at = datetime.utcnow()

    return schemas.FoodCartOut(
        student_id=student_id,
        shop_id=resolved_shop_id,
        items=cart_items,
        total_items=len(cart_items),
        total_quantity=total_quantity,
        total_price=total_price,
        checkout_preview_open=checkout_preview_open,
        checkout_delivery_point=delivery_point,
        updated_at=updated_at,
    )


def _cart_items_to_docs(items: list[schemas.FoodCartItemOut]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for item in items:
        docs.append(
            {
                "cart_key": item.cart_key,
                "shop_id": int(item.shop_id),
                "menu_item_id": int(item.menu_item_id),
                "food_item_id": (int(item.food_item_id) if item.food_item_id else None),
                "name": item.name,
                "price": round(float(item.price), 2),
                "quantity": int(item.quantity),
                "item_note": str(item.item_note or "").strip(),
                "updated_at": datetime.utcnow(),
            }
        )
    return docs


def _menu_item_to_out(item: models.FoodMenuItem) -> schemas.FoodMenuItemOut:
    return schemas.FoodMenuItemOut(
        id=item.id,
        shop_id=item.shop_id,
        name=item.name,
        description=item.description,
        base_price=item.base_price,
        is_veg=bool(item.is_veg),
        spicy_level=int(item.spicy_level or 0),
        variants=_serialize_json(item.variants_json),
        addons=_serialize_json(item.addons_json),
        available_from=item.available_from,
        available_to=item.available_to,
        prep_time_override_minutes=item.prep_time_override_minutes,
        stock_quantity=item.stock_quantity,
        sold_out=bool(item.sold_out),
        is_active=bool(item.is_active),
    )


def _resolve_legacy_food_item_for_menu(
    db: Session,
    *,
    menu_item: models.FoodMenuItem,
    explicit_food_item_id: int | None,
) -> models.FoodItem:
    legacy_item = db.get(models.FoodItem, explicit_food_item_id) if explicit_food_item_id else None
    if explicit_food_item_id and not legacy_item:
        raise HTTPException(status_code=404, detail="Linked food item not found")
    if explicit_food_item_id and legacy_item and not legacy_item.is_active:
        raise HTTPException(status_code=400, detail="Food item is inactive")

    if legacy_item is None:
        legacy_item = (
            db.query(models.FoodItem)
            .filter(func.lower(models.FoodItem.name) == menu_item.name.strip().lower())
            .first()
        )
        if legacy_item is None:
            legacy_item = models.FoodItem(
                name=menu_item.name.strip(),
                price=float(menu_item.base_price),
                is_active=True,
            )
            db.add(legacy_item)
            db.flush()
        elif not legacy_item.is_active:
            legacy_item.is_active = True
            legacy_item.price = float(menu_item.base_price)
    return legacy_item


def _resolve_prep_eta_minutes(
    *,
    menu_item: models.FoodMenuItem | None,
    shop: models.FoodShop | None,
) -> int | None:
    if menu_item and menu_item.prep_time_override_minutes:
        return max(1, int(menu_item.prep_time_override_minutes))
    if shop and shop.average_prep_minutes:
        return max(1, int(shop.average_prep_minutes))
    return None


def _assert_shop_owner_access(current_user: CurrentUser, shop: models.FoodShop) -> None:
    if current_user.role in (models.UserRole.ADMIN, models.UserRole.FACULTY):
        return
    if current_user.role == models.UserRole.OWNER and shop.owner_user_id == current_user.id:
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions for this shop")


def _enforce_order_rate_limit(student_id: int) -> None:
    now = datetime.utcnow()
    window = timedelta(seconds=_rate_limit_window_seconds())
    with _order_rate_lock:
        bucket = _order_rate_buckets.setdefault(int(student_id), [])
        bucket[:] = [stamp for stamp in bucket if now - stamp <= window]
        if len(bucket) >= _rate_limit_max_orders():
            retry_after = max(1, int(window.total_seconds()))
            raise HTTPException(
                status_code=429,
                detail="Too many order attempts. Please wait before placing another order.",
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)


def _is_order_final(status_value: models.FoodOrderStatus) -> bool:
    return status_value in {
        models.FoodOrderStatus.DELIVERED,
        models.FoodOrderStatus.CANCELLED,
        models.FoodOrderStatus.REJECTED,
        models.FoodOrderStatus.REFUNDED,
    }


def _normalize_webhook_payment_state(raw_status: str) -> tuple[str, str, str]:
    webhook_status = str(raw_status or "").strip().lower()
    if webhook_status in {"paid", "captured", "verified", "success"}:
        return ("paid", "captured", "paid")
    if webhook_status in {"attempted", "authorized"}:
        return ("attempted", webhook_status, "attempted")
    return ("attempted", "failed", "failed")


def _is_payment_paid(payment: models.FoodPayment) -> bool:
    return str(payment.status or "").strip().lower() == "paid"


def _normalize_razorpay_gateway_status(raw_status: str | None) -> str | None:
    status_value = str(raw_status or "").strip().lower()
    if not status_value:
        return None
    if status_value in {"captured", "paid", "success"}:
        return "paid"
    if status_value in {"failed", "refunded"}:
        return "failed"
    if status_value in {"authorized", "created", "attempted"}:
        return "attempted"
    return None


def _fetch_razorpay_gateway_status(
    *,
    provider_order_id: str | None,
    provider_payment_id: str | None,
) -> tuple[str | None, str | None]:
    rzp = _get_razorpay_client()
    resolved_status: str | None = None
    resolved_payment_id = str(provider_payment_id or "").strip() or None
    resolved_order_id = str(provider_order_id or "").strip() or None
    if not rzp:
        return resolved_status, resolved_payment_id

    if resolved_payment_id:
        try:
            payment_entity = rzp.payment.fetch(resolved_payment_id) or {}
            if isinstance(payment_entity, dict):
                normalized = _normalize_razorpay_gateway_status(payment_entity.get("status"))
                if normalized:
                    resolved_status = normalized
                fetched_order_id = str(payment_entity.get("order_id") or "").strip() or None
                if fetched_order_id:
                    resolved_order_id = resolved_order_id or fetched_order_id
        except Exception:
            pass

    if resolved_order_id and resolved_status != "paid":
        try:
            payments_payload = rzp.order.payments(resolved_order_id) or {}
            rows = payments_payload.get("items") if isinstance(payments_payload, dict) else []
            if isinstance(rows, list):
                best_rank = 0
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    normalized = _normalize_razorpay_gateway_status(row.get("status"))
                    if not normalized:
                        continue
                    rank = 3 if normalized == "paid" else (2 if normalized == "attempted" else 1)
                    if rank > best_rank:
                        best_rank = rank
                        resolved_status = normalized
                        fetched_payment_id = str(row.get("id") or "").strip() or None
                        if fetched_payment_id:
                            resolved_payment_id = fetched_payment_id
                    if rank == 3:
                        break
        except Exception:
            pass

    return resolved_status, resolved_payment_id


def _extract_razorpay_webhook_fields(raw_payload: dict[str, Any]) -> tuple[str | None, str | None, str | None, dict[str, Any]]:
    event_name = str(raw_payload.get("event") or "").strip().lower()
    payload_block = raw_payload.get("payload") if isinstance(raw_payload.get("payload"), dict) else {}
    payment_block = payload_block.get("payment") if isinstance(payload_block.get("payment"), dict) else {}
    payment_entity = payment_block.get("entity") if isinstance(payment_block.get("entity"), dict) else {}
    order_block = payload_block.get("order") if isinstance(payload_block.get("order"), dict) else {}
    order_entity = order_block.get("entity") if isinstance(order_block.get("entity"), dict) else {}

    provider_order_id = str(
        payment_entity.get("order_id")
        or order_entity.get("id")
        or ""
    ).strip() or None
    provider_payment_id = str(payment_entity.get("id") or "").strip() or None
    payment_status = str(payment_entity.get("status") or "").strip().lower() or None

    normalized_status = None
    if event_name in {"payment.captured", "order.paid"}:
        normalized_status = "paid"
    elif event_name in {"payment.failed"}:
        normalized_status = "failed"
    elif event_name in {"payment.authorized", "payment.created"}:
        normalized_status = "authorized"
    elif payment_status:
        normalized_status = payment_status

    normalized_payload: dict[str, Any] = {
        "event": event_name or None,
        "payment_status": payment_status,
        "provider_order_id": provider_order_id,
        "provider_payment_id": provider_payment_id,
    }
    if payment_entity:
        normalized_payload["payment"] = payment_entity
    if order_entity:
        normalized_payload["order"] = order_entity
    return provider_order_id, provider_payment_id, normalized_status, normalized_payload


def _verify_razorpay_webhook_signature(*, secret: str, raw_body: bytes, incoming_signature: str) -> bool:
    shared_secret = str(secret or "").strip()
    signature = str(incoming_signature or "").strip()
    if not shared_secret or not signature:
        return False
    digest = hmac.new(shared_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def _register_payment_webhook_event(
    *,
    mongo_db,
    provider: str,
    event_id: str | None,
    fingerprint: str,
    signature: str | None,
    payload: dict,
) -> bool:
    now = datetime.utcnow()
    body = {
        "provider": provider,
        "event_id": (str(event_id or "").strip() or None),
        "fingerprint": fingerprint,
        "signature": (str(signature or "").strip() or None),
        "payload": payload,
        "created_at": now,
    }
    try:
        mongo_db["payment_webhook_events"].insert_one(body)
        return False
    except DuplicateKeyError:
        return True


def _sync_order_document(order: models.FoodOrder, source: str) -> None:
    mirror_document(
        "food_orders",
        {
            "id": order.id,
            "order_id": order.id,
            "student_id": order.student_id,
            "shop_id": order.shop_id,
            "menu_item_id": order.menu_item_id,
            "food_item_id": order.food_item_id,
            "slot_id": order.slot_id,
            "order_date": order.order_date.isoformat(),
            "quantity": order.quantity,
            "unit_price": order.unit_price,
            "total_price": order.total_price,
            "status": order.status.value,
            "shop_name": order.shop_name,
            "shop_block": order.shop_block,
            "idempotency_key": order.idempotency_key,
            "payment_status": order.payment_status,
            "payment_provider": order.payment_provider,
            "payment_reference": order.payment_reference,
            "status_note": order.status_note,
            "assigned_runner": order.assigned_runner,
            "pickup_point": order.pickup_point,
            "delivery_eta_minutes": order.delivery_eta_minutes,
            "estimated_ready_at": order.estimated_ready_at,
            "location_verified": bool(order.location_verified),
            "location_latitude": order.location_latitude,
            "location_longitude": order.location_longitude,
            "location_accuracy_m": order.location_accuracy_m,
            "last_location_verified_at": order.last_location_verified_at,
            "verified_at": order.verified_at,
            "preparing_at": order.preparing_at,
            "out_for_delivery_at": order.out_for_delivery_at,
            "delivered_at": order.delivered_at,
            "cancelled_at": order.cancelled_at,
            "cancel_reason": order.cancel_reason,
            "rating_stars": order.rating_stars,
            "rating_comment": order.rating_comment,
            "rated_at": order.rated_at,
            "rating_locked_at": order.rating_locked_at,
            "last_status_updated_at": order.last_status_updated_at,
            "created_at": order.created_at,
            "source": source,
        },
        upsert_filter={"order_id": order.id},
    )


def _record_order_audit(
    db: Session,
    order: models.FoodOrder,
    *,
    event_type: str,
    actor: CurrentUser | None,
    from_status: str | None = None,
    to_status: str | None = None,
    message: str | None = None,
    payload: dict | None = None,
) -> None:
    row = models.FoodOrderAudit(
        order_id=order.id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        actor_role=(actor.role.value if actor else None),
        actor_id=(actor.id if actor else None),
        actor_email=(actor.email if actor else None),
        message=message,
        payload_json=(json.dumps(payload, default=str) if payload else None),
    )
    db.add(row)
    mirror_document(
        "food_order_audit",
        {
            "order_id": order.id,
            "event_type": event_type,
            "from_status": from_status,
            "to_status": to_status,
            "actor_role": row.actor_role,
            "actor_id": row.actor_id,
            "actor_email": row.actor_email,
            "message": message,
            "payload": payload or {},
            "created_at": datetime.utcnow(),
        },
    )
    mirror_event(
        "food.order.audit",
        {
            "order_id": order.id,
            "event_type": event_type,
            "from_status": from_status,
            "to_status": to_status,
            "message": message,
        },
        source="food-router",
        actor={"id": actor.id, "email": actor.email, "role": actor.role.value} if actor else None,
    )


def _notify_order_status(db: Session, order: models.FoodOrder, message: str) -> None:
    student = db.get(models.Student, order.student_id)
    if not student:
        return
    row = models.NotificationLog(
        student_id=order.student_id,
        message=message[:500],
        channel="in-app",
        sent_to=student.email,
    )
    db.add(row)
    db.flush()
    mirror_document(
        "notification_logs",
        {
            "id": row.id,
            "student_id": order.student_id,
            "message": row.message,
            "channel": row.channel,
            "sent_to": row.sent_to,
            "created_at": datetime.utcnow(),
            "source": "food-status",
        },
        upsert_filter={"id": row.id},
    )


def _refresh_shop_rating_from_orders(db: Session, shop_id: int | None) -> tuple[models.FoodShop | None, int]:
    if not shop_id:
        return None, 0
    shop = db.get(models.FoodShop, int(shop_id))
    if not shop:
        return None, 0

    average_rating, ratings_count = (
        db.query(
            func.avg(models.FoodOrder.rating_stars),
            func.count(models.FoodOrder.id),
        )
        .filter(
            models.FoodOrder.shop_id == shop.id,
            models.FoodOrder.status == models.FoodOrderStatus.DELIVERED,
            models.FoodOrder.rating_stars.isnot(None),
        )
        .one()
    )

    resolved_count = int(ratings_count or 0)
    if resolved_count <= 0 or average_rating is None:
        shop.rating = 4.0
    else:
        shop.rating = round(float(average_rating), 2)
    shop.updated_at = datetime.utcnow()
    return shop, resolved_count


def _status_transition_allowed(current_status: models.FoodOrderStatus, new_status: models.FoodOrderStatus) -> bool:
    allowed_map = {
        models.FoodOrderStatus.PLACED: {
            models.FoodOrderStatus.VERIFIED,
            models.FoodOrderStatus.REJECTED,
            models.FoodOrderStatus.CANCELLED,
            models.FoodOrderStatus.PREPARING,
        },
        models.FoodOrderStatus.VERIFIED: {
            models.FoodOrderStatus.PREPARING,
            models.FoodOrderStatus.CANCELLED,
        },
        models.FoodOrderStatus.PREPARING: {
            models.FoodOrderStatus.READY,
            models.FoodOrderStatus.OUT_FOR_DELIVERY,
            models.FoodOrderStatus.CANCELLED,
        },
        models.FoodOrderStatus.READY: {
            models.FoodOrderStatus.COLLECTED,
            models.FoodOrderStatus.OUT_FOR_DELIVERY,
            models.FoodOrderStatus.CANCELLED,
        },
        models.FoodOrderStatus.COLLECTED: {
            models.FoodOrderStatus.DELIVERED,
        },
        models.FoodOrderStatus.OUT_FOR_DELIVERY: {
            models.FoodOrderStatus.DELIVERED,
            models.FoodOrderStatus.CANCELLED,
        },
        models.FoodOrderStatus.REJECTED: {
            models.FoodOrderStatus.REFUND_PENDING,
        },
        models.FoodOrderStatus.CANCELLED: {
            models.FoodOrderStatus.REFUND_PENDING,
        },
        models.FoodOrderStatus.REFUND_PENDING: {
            models.FoodOrderStatus.REFUNDED,
        },
    }
    if current_status == new_status:
        return True
    return new_status in allowed_map.get(current_status, set())


def _apply_status_transition(order: models.FoodOrder, new_status: models.FoodOrderStatus, *, note: str | None) -> None:
    now = datetime.utcnow()
    order.status = new_status
    order.last_status_updated_at = now
    if note:
        order.status_note = note
    if new_status == models.FoodOrderStatus.VERIFIED:
        order.verified_at = now
    elif new_status == models.FoodOrderStatus.PREPARING:
        order.preparing_at = now
        if not order.estimated_ready_at and order.delivery_eta_minutes:
            order.estimated_ready_at = now + timedelta(minutes=order.delivery_eta_minutes)
    elif new_status == models.FoodOrderStatus.OUT_FOR_DELIVERY:
        order.out_for_delivery_at = now
    elif new_status == models.FoodOrderStatus.DELIVERED:
        order.delivered_at = now
    elif new_status == models.FoodOrderStatus.CANCELLED:
        order.cancelled_at = now
    elif new_status == models.FoodOrderStatus.REJECTED:
        order.cancelled_at = now


def _enforce_order_timeout(order: models.FoodOrder) -> bool:
    if order.status != models.FoodOrderStatus.PLACED:
        return False
    if (datetime.utcnow() - order.created_at).total_seconds() < (_order_timeout_minutes() * 60):
        return False
    _apply_status_transition(order, models.FoodOrderStatus.CANCELLED, note="Auto-cancelled: verification timeout")
    order.cancel_reason = "verification_timeout"
    return True


def _order_visible_to_owner_filter(query, db: Session, owner_user_id: int):
    shops = (
        db.query(models.FoodShop.id, models.FoodShop.name)
        .filter(models.FoodShop.owner_user_id == owner_user_id)
        .all()
    )
    shop_ids = [row.id for row in shops]
    shop_names = [row.name for row in shops]
    if not shop_ids and not shop_names:
        return query.filter(text("1 = 0"))
    return query.filter(
        (models.FoodOrder.shop_id.in_(shop_ids) if shop_ids else text("0 = 1"))
        | (models.FoodOrder.shop_name.in_(shop_names) if shop_names else text("0 = 1"))
    )


def _scope_order_query_for_user(query, db: Session, current_user: CurrentUser):
    if current_user.role == models.UserRole.ADMIN:
        return query
    if current_user.role == models.UserRole.OWNER:
        return _order_visible_to_owner_filter(query, db, current_user.id)
    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly")
        return query.filter(models.FoodOrder.student_id == current_user.student_id)
    # Faculty users can monitor aggregated metrics but must not see per-user order rows.
    return query.filter(text("1 = 0"))


def _query_food_slots(db: Session) -> list[models.BreakSlot]:
    rows = (
        db.query(models.BreakSlot)
        .filter(
            models.BreakSlot.start_time >= dt_time(10, 0),
            models.BreakSlot.end_time <= dt_time(21, 0),
        )
        .order_by(models.BreakSlot.start_time.asc())
        .all()
    )
    if rows:
        return rows
    return db.query(models.BreakSlot).order_by(models.BreakSlot.start_time.asc()).all()


def _save_food_cart(
    *,
    mongo_db,
    student_id: int,
    user_id: int,
    shop_id: int | None,
    items: list[dict[str, Any]],
    checkout_preview_open: bool,
    checkout_delivery_point: str | None,
) -> schemas.FoodCartOut:
    now = datetime.utcnow()
    safe_items = [dict(item) for item in items if isinstance(item, dict)]
    if not safe_items:
        shop_id = None
        checkout_preview_open = False
        checkout_delivery_point = None

    update_payload: dict[str, Any] = {
        "student_id": int(student_id),
        "user_id": int(user_id),
        "shop_id": int(shop_id) if shop_id else None,
        "items": safe_items,
        "checkout_preview_open": bool(checkout_preview_open) and bool(safe_items),
        "checkout_delivery_point": (str(checkout_delivery_point).strip() or None) if checkout_delivery_point else None,
        "updated_at": now,
    }

    mongo_db["food_carts"].update_one(
        {"student_id": int(student_id)},
        {
            "$set": update_payload,
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    saved = mongo_db["food_carts"].find_one({"student_id": int(student_id)})
    return _food_cart_to_out(saved, student_id=int(student_id))


def _clear_food_cart(
    *,
    mongo_db,
    student_id: int,
    user_id: int,
) -> schemas.FoodCartOut:
    return _save_food_cart(
        mongo_db=mongo_db,
        student_id=student_id,
        user_id=user_id,
        shop_id=None,
        items=[],
        checkout_preview_open=False,
        checkout_delivery_point=None,
    )


def _try_clear_food_cart(
    *,
    student_id: int,
    user_id: int | None = None,
) -> None:
    mongo_db = get_mongo_db(required=False)
    if mongo_db is None:
        return
    _clear_food_cart(
        mongo_db=mongo_db,
        student_id=student_id,
        user_id=(int(user_id) if user_id is not None else int(student_id)),
    )


def _food_catalog_counts(db: Session) -> dict[str, int]:
    return {
        "shops": int(db.query(func.count(models.FoodShop.id)).scalar() or 0),
        "menu_items": int(db.query(func.count(models.FoodMenuItem.id)).scalar() or 0),
        "slots": int(db.query(func.count(models.BreakSlot.id)).scalar() or 0),
        "items": int(db.query(func.count(models.FoodItem.id)).scalar() or 0),
    }


def _ensure_food_catalog_seeded(db: Session) -> dict[str, object]:
    """
    Self-heal food catalog in case the runtime points to a fresh/partial SQL snapshot.
    """
    before = _food_catalog_counts(db)
    needs_bootstrap = (
        before["shops"] < 20
        or before["menu_items"] < 80
        or before["slots"] < 11
        or before["items"] < 80
    )
    summary = None
    if needs_bootstrap:
        summary = bootstrap_food_hall_catalog(db)
    after = _food_catalog_counts(db)
    return {"seeded": bool(needs_bootstrap), "before": before, "after": after, "summary": summary}


@router.post("/location/verify", response_model=schemas.FoodDeliveryLocationCheckOut)
def verify_location_gate(
    payload: schemas.FoodDeliveryLocationCheckRequest,
    _: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER)
    ),
):
    allowed, message, distance_m = _evaluate_location_gate(
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy_m,
    )
    return schemas.FoodDeliveryLocationCheckOut(
        allowed=allowed,
        message=message,
        distance_m=round(distance_m, 2),
        radius_m=round(_lpu_radius_meters(), 2),
        max_accuracy_m=round(_max_location_accuracy_m(), 2),
        center_latitude=_lpu_center_latitude(),
        center_longitude=_lpu_center_longitude(),
    )


@router.post("/bootstrap/catalog", response_model=schemas.MessageResponse)
def bootstrap_food_catalog(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    summary = bootstrap_food_hall_catalog(db)
    return schemas.MessageResponse(
        message=(
            "Food catalog synced. "
            f"Shops +{summary['shops_created']}, menu +{summary['menu_created']}, slots +{summary['slots_created']}."
        )
    )


@router.post("/bootstrap/ensure", response_model=schemas.MessageResponse)
def ensure_food_catalog(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT)
    ),
):
    result = _ensure_food_catalog_seeded(db)
    if result["seeded"]:
        after = result["after"]
        return schemas.MessageResponse(
            message=(
                "Food catalog repaired. "
                f"Shops={after['shops']}, Menu Items={after['menu_items']}, Slots={after['slots']}."
            )
        )
    after = result["after"]
    return schemas.MessageResponse(
        message=(
            "Food catalog already configured. "
            f"Shops={after['shops']}, Menu Items={after['menu_items']}, Slots={after['slots']}."
        )
    )


@router.post("/shops", response_model=schemas.FoodShopOut, status_code=status.HTTP_201_CREATED)
def create_food_shop(
    payload: schemas.FoodShopCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    existing = (
        db.query(models.FoodShop)
        .filter(models.FoodShop.name == payload.name, models.FoodShop.block == payload.block)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Shop already exists in this block")
    shop = models.FoodShop(**payload.model_dump(), updated_at=datetime.utcnow())
    db.add(shop)
    db.commit()
    db.refresh(shop)
    mirror_document(
        "food_shops",
        {
            "id": shop.id,
            "shop_id": shop.id,
            "name": shop.name,
            "block": shop.block,
            "owner_user_id": shop.owner_user_id,
            "is_active": shop.is_active,
            "is_popular": shop.is_popular,
            "rating": shop.rating,
            "average_prep_minutes": shop.average_prep_minutes,
            "created_at": shop.created_at,
            "source": "shop-create",
        },
        upsert_filter={"shop_id": shop.id},
    )
    return shop


@router.get("/shops", response_model=list[schemas.FoodShopOut])
def list_food_shops(
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER)
    ),
):
    _ensure_food_catalog_seeded(db)
    query = db.query(models.FoodShop)
    if active_only:
        query = query.filter(models.FoodShop.is_active.is_(True))
    if current_user.role == models.UserRole.OWNER:
        query = query.filter(models.FoodShop.owner_user_id == current_user.id)
    return query.order_by(models.FoodShop.block.asc(), models.FoodShop.name.asc()).all()


@router.patch("/shops/{shop_id}", response_model=schemas.FoodShopOut)
def update_food_shop(
    shop_id: int,
    payload: schemas.FoodShopUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.OWNER)),
):
    shop = db.get(models.FoodShop, shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    _assert_shop_owner_access(current_user, shop)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(shop, key, value)
    shop.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(shop)
    mirror_document(
        "food_shops",
        {
            "id": shop.id,
            "shop_id": shop.id,
            "name": shop.name,
            "block": shop.block,
            "owner_user_id": shop.owner_user_id,
            "is_active": shop.is_active,
            "is_popular": shop.is_popular,
            "rating": shop.rating,
            "average_prep_minutes": shop.average_prep_minutes,
            "updated_at": shop.updated_at,
            "source": "shop-update",
        },
        upsert_filter={"shop_id": shop.id},
    )
    return shop


@router.post("/shops/{shop_id}/menu-items", response_model=schemas.FoodMenuItemOut, status_code=status.HTTP_201_CREATED)
def create_food_menu_item(
    shop_id: int,
    payload: schemas.FoodMenuItemCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.OWNER)),
):
    if payload.shop_id != shop_id:
        raise HTTPException(status_code=400, detail="shop_id mismatch")
    shop = db.get(models.FoodShop, shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    _assert_shop_owner_access(current_user, shop)
    existing = (
        db.query(models.FoodMenuItem)
        .filter(models.FoodMenuItem.shop_id == shop_id, models.FoodMenuItem.name == payload.name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Menu item already exists for this shop")

    row = models.FoodMenuItem(
        shop_id=shop_id,
        name=payload.name,
        description=payload.description,
        base_price=payload.base_price,
        is_veg=payload.is_veg,
        spicy_level=payload.spicy_level,
        variants_json=json.dumps(payload.variants or []),
        addons_json=json.dumps(payload.addons or []),
        available_from=payload.available_from,
        available_to=payload.available_to,
        prep_time_override_minutes=payload.prep_time_override_minutes,
        stock_quantity=payload.stock_quantity,
        sold_out=payload.sold_out,
        is_active=payload.is_active,
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    mirror_document(
        "food_menu_items",
        {
            "id": row.id,
            "menu_item_id": row.id,
            "shop_id": row.shop_id,
            "name": row.name,
            "description": row.description,
            "base_price": row.base_price,
            "is_veg": row.is_veg,
            "spicy_level": row.spicy_level,
            "variants": payload.variants or [],
            "addons": payload.addons or [],
            "available_from": str(row.available_from) if row.available_from else None,
            "available_to": str(row.available_to) if row.available_to else None,
            "prep_time_override_minutes": row.prep_time_override_minutes,
            "stock_quantity": row.stock_quantity,
            "sold_out": row.sold_out,
            "is_active": row.is_active,
            "created_at": row.created_at,
            "source": "menu-create",
        },
        upsert_filter={"menu_item_id": row.id},
    )
    return _menu_item_to_out(row)


@router.get("/shops/{shop_id}/menu-items", response_model=list[schemas.FoodMenuItemOut])
def list_food_menu_items(
    shop_id: int,
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER)
    ),
):
    if not db.get(models.FoodShop, shop_id):
        raise HTTPException(status_code=404, detail="Shop not found")
    query = db.query(models.FoodMenuItem).filter(models.FoodMenuItem.shop_id == shop_id)
    if active_only:
        query = query.filter(models.FoodMenuItem.is_active.is_(True), models.FoodMenuItem.sold_out.is_(False))
    rows = query.order_by(models.FoodMenuItem.name.asc()).all()
    return [_menu_item_to_out(item) for item in rows]


@router.patch("/menu-items/{menu_item_id}", response_model=schemas.FoodMenuItemOut)
def update_food_menu_item(
    menu_item_id: int,
    payload: schemas.FoodMenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.OWNER)),
):
    row = db.get(models.FoodMenuItem, menu_item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Menu item not found")
    shop = db.get(models.FoodShop, row.shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    _assert_shop_owner_access(current_user, shop)

    updates = payload.model_dump(exclude_unset=True)
    if "variants" in updates:
        updates["variants_json"] = json.dumps(updates.pop("variants") or [])
    if "addons" in updates:
        updates["addons_json"] = json.dumps(updates.pop("addons") or [])
    for key, value in updates.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    mirror_document(
        "food_menu_items",
        {
            "id": row.id,
            "menu_item_id": row.id,
            "shop_id": row.shop_id,
            "name": row.name,
            "description": row.description,
            "base_price": row.base_price,
            "is_veg": row.is_veg,
            "spicy_level": row.spicy_level,
            "variants": _serialize_json(row.variants_json),
            "addons": _serialize_json(row.addons_json),
            "available_from": str(row.available_from) if row.available_from else None,
            "available_to": str(row.available_to) if row.available_to else None,
            "prep_time_override_minutes": row.prep_time_override_minutes,
            "stock_quantity": row.stock_quantity,
            "sold_out": row.sold_out,
            "is_active": row.is_active,
            "updated_at": row.updated_at,
            "source": "menu-update",
        },
        upsert_filter={"menu_item_id": row.id},
    )
    return _menu_item_to_out(row)


@router.post("/items", response_model=schemas.FoodItemOut, status_code=status.HTTP_201_CREATED)
def create_food_item(
    payload: schemas.FoodItemCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    exists = db.query(models.FoodItem).filter(models.FoodItem.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=409, detail="Food item already exists")
    item = models.FoodItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)

    mirror_document(
        "food_items",
        {
            "id": item.id,
            "food_item_id": item.id,
            "name": item.name,
            "price": item.price,
            "is_active": item.is_active,
            "created_at": datetime.utcnow(),
            "source": "api",
        },
        upsert_filter={"food_item_id": item.id},
    )

    return item


@router.get("/items", response_model=list[schemas.FoodItemOut])
def list_food_items(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER)
    ),
):
    _ensure_food_catalog_seeded(db)
    return db.query(models.FoodItem).order_by(models.FoodItem.name.asc()).all()


@router.post("/slots", response_model=schemas.BreakSlotOut, status_code=status.HTTP_201_CREATED)
def create_break_slot(
    payload: schemas.BreakSlotCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY)),
):
    exists = db.query(models.BreakSlot).filter(models.BreakSlot.label == payload.label).first()
    if exists:
        raise HTTPException(status_code=409, detail="Break slot already exists")
    slot = models.BreakSlot(**payload.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)

    mirror_document(
        "break_slots",
        {
            "id": slot.id,
            "slot_id": slot.id,
            "label": slot.label,
            "start_time": str(slot.start_time),
            "end_time": str(slot.end_time),
            "max_orders": slot.max_orders,
            "created_at": datetime.utcnow(),
            "source": "api",
        },
        upsert_filter={"slot_id": slot.id},
    )

    return slot


@router.get("/slots", response_model=list[schemas.BreakSlotOut])
def list_break_slots(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER)
    ),
):
    _ensure_food_catalog_seeded(db)
    rows = _query_food_slots(db)
    if len(rows) < 11:
        _ensure_food_catalog_seeded(db)
        rows = _query_food_slots(db)
    return rows


@router.get("/cart", response_model=schemas.FoodCartOut)
def get_food_cart(
    current_user: CurrentUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student_id = _require_student_id(current_user)
    mongo_db = _mongo_db_or_503()
    doc = mongo_db["food_carts"].find_one({"student_id": student_id})
    return _food_cart_to_out(doc, student_id=student_id)


@router.post("/cart/items", response_model=schemas.FoodCartOut)
def mutate_food_cart_item(
    payload: schemas.FoodCartItemMutationRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student_id = _require_student_id(current_user)
    _ensure_food_catalog_seeded(db)
    shop = db.get(models.FoodShop, payload.shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    if not shop.is_active:
        raise HTTPException(status_code=409, detail="Shop is not active")

    menu_item = db.get(models.FoodMenuItem, payload.menu_item_id)
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    if int(menu_item.shop_id) != int(payload.shop_id):
        raise HTTPException(status_code=400, detail="Menu item does not belong to selected shop")
    if payload.quantity_delta > 0:
        if not menu_item.is_active or menu_item.sold_out:
            raise HTTPException(status_code=409, detail="Selected menu item is unavailable")
        if menu_item.stock_quantity is not None and int(menu_item.stock_quantity) <= 0:
            raise HTTPException(status_code=409, detail="Selected menu item is out of stock")

    food_item_id: int | None = None
    if payload.food_item_id:
        linked = db.get(models.FoodItem, payload.food_item_id)
        if not linked:
            raise HTTPException(status_code=404, detail="Linked food item not found")
        food_item_id = int(linked.id)

    clean_note = str(payload.item_note or "").strip()[:240]
    cart_key = _build_cart_key(menu_item.id, clean_note)
    display_name = menu_item.name.strip()[:160] or str(payload.name).strip()[:160] or f"Item #{menu_item.id}"
    if clean_note:
        display_name = f"{display_name} ({clean_note})"
    unit_price = round(float(menu_item.base_price), 2)
    delta = int(payload.quantity_delta)

    mongo_db = _mongo_db_or_503()
    existing_doc = mongo_db["food_carts"].find_one({"student_id": student_id})
    current_cart = _food_cart_to_out(existing_doc, student_id=student_id)
    existing_items = _cart_items_to_docs(current_cart.items)
    shop_id = int(current_cart.shop_id) if current_cart.shop_id else None

    existing_index = next(
        (idx for idx, entry in enumerate(existing_items) if str(entry.get("cart_key", "")).strip() == cart_key),
        -1,
    )
    if shop_id and shop_id != int(shop.id) and delta > 0 and existing_index < 0:
        raise HTTPException(
            status_code=409,
            detail="Orders are accepted only from a single shop at a time. Clear or checkout the current cart first.",
        )

    if existing_index >= 0:
        row = existing_items[existing_index]
        next_qty = int(row.get("quantity", 0)) + delta
        if next_qty <= 0:
            existing_items.pop(existing_index)
        else:
            row["quantity"] = next_qty
            row["price"] = unit_price
            row["name"] = display_name
            row["item_note"] = clean_note
            row["shop_id"] = int(shop.id)
            row["menu_item_id"] = int(menu_item.id)
            row["food_item_id"] = food_item_id
            row["updated_at"] = datetime.utcnow()
    elif delta > 0:
        existing_items.append(
            {
                "cart_key": cart_key,
                "shop_id": int(shop.id),
                "menu_item_id": int(menu_item.id),
                "food_item_id": food_item_id,
                "name": display_name,
                "price": unit_price,
                "quantity": delta,
                "item_note": clean_note,
                "updated_at": datetime.utcnow(),
            }
        )

    resolved_shop_id = int(shop.id) if existing_items else None
    if existing_items:
        # Keep all rows pinned to one shop so checkout constraints remain deterministic.
        for row in existing_items:
            row["shop_id"] = int(resolved_shop_id)

    saved = _save_food_cart(
        mongo_db=mongo_db,
        student_id=student_id,
        user_id=current_user.id,
        shop_id=resolved_shop_id,
        items=existing_items,
        checkout_preview_open=current_cart.checkout_preview_open,
        checkout_delivery_point=current_cart.checkout_delivery_point,
    )
    mirror_event(
        "food.cart.item.mutated",
        {
            "student_id": student_id,
            "cart_key": cart_key,
            "menu_item_id": int(menu_item.id),
            "shop_id": int(shop.id),
            "quantity_delta": delta,
            "total_items": saved.total_items,
            "total_quantity": saved.total_quantity,
        },
        source="food-router",
        actor={"id": current_user.id, "email": current_user.email, "role": current_user.role.value},
    )
    return saved


@router.patch("/cart/state", response_model=schemas.FoodCartOut)
def update_food_cart_state(
    payload: schemas.FoodCartStateUpdateRequest,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student_id = _require_student_id(current_user)
    mongo_db = _mongo_db_or_503()
    existing_doc = mongo_db["food_carts"].find_one({"student_id": student_id})
    current_cart = _food_cart_to_out(existing_doc, student_id=student_id)
    item_docs = _cart_items_to_docs(current_cart.items)

    checkout_preview_open = current_cart.checkout_preview_open
    if payload.checkout_preview_open is not None:
        checkout_preview_open = bool(payload.checkout_preview_open)

    checkout_delivery_point = current_cart.checkout_delivery_point
    if payload.checkout_delivery_point is not None:
        checkout_delivery_point = str(payload.checkout_delivery_point or "").strip() or None

    saved = _save_food_cart(
        mongo_db=mongo_db,
        student_id=student_id,
        user_id=current_user.id,
        shop_id=current_cart.shop_id,
        items=item_docs,
        checkout_preview_open=checkout_preview_open,
        checkout_delivery_point=checkout_delivery_point,
    )
    mirror_event(
        "food.cart.state.updated",
        {
            "student_id": student_id,
            "checkout_preview_open": saved.checkout_preview_open,
            "checkout_delivery_point": saved.checkout_delivery_point,
            "total_items": saved.total_items,
        },
        source="food-router",
        actor={"id": current_user.id, "email": current_user.email, "role": current_user.role.value},
    )
    return saved


@router.delete("/cart/items/{cart_key:path}", response_model=schemas.FoodCartOut)
def remove_food_cart_item(
    cart_key: str,
    current_user: CurrentUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student_id = _require_student_id(current_user)
    cleaned_key = str(cart_key or "").strip()
    if not cleaned_key:
        raise HTTPException(status_code=400, detail="cart_key is required")

    mongo_db = _mongo_db_or_503()
    existing_doc = mongo_db["food_carts"].find_one({"student_id": student_id})
    current_cart = _food_cart_to_out(existing_doc, student_id=student_id)
    item_docs = _cart_items_to_docs(current_cart.items)
    remaining_items = [row for row in item_docs if str(row.get("cart_key", "")).strip() != cleaned_key]
    resolved_shop_id = int(current_cart.shop_id) if current_cart.shop_id and remaining_items else None

    saved = _save_food_cart(
        mongo_db=mongo_db,
        student_id=student_id,
        user_id=current_user.id,
        shop_id=resolved_shop_id,
        items=remaining_items,
        checkout_preview_open=current_cart.checkout_preview_open,
        checkout_delivery_point=current_cart.checkout_delivery_point,
    )
    mirror_event(
        "food.cart.item.removed",
        {
            "student_id": student_id,
            "cart_key": cleaned_key,
            "total_items": saved.total_items,
            "total_quantity": saved.total_quantity,
        },
        source="food-router",
        actor={"id": current_user.id, "email": current_user.email, "role": current_user.role.value},
    )
    return saved


@router.delete("/cart", response_model=schemas.FoodCartOut)
def clear_food_cart(
    current_user: CurrentUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    student_id = _require_student_id(current_user)
    mongo_db = _mongo_db_or_503()
    saved = _clear_food_cart(mongo_db=mongo_db, student_id=student_id, user_id=current_user.id)
    mirror_event(
        "food.cart.cleared",
        {"student_id": student_id},
        source="food-router",
        actor={"id": current_user.id, "email": current_user.email, "role": current_user.role.value},
    )
    return saved


@router.post("/orders", response_model=schemas.FoodOrderOut, status_code=status.HTTP_201_CREATED)
def create_food_order(
    payload: schemas.FoodOrderCreate,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.STUDENT)),
):
    _ensure_food_catalog_seeded(db)
    idempotency_key = (payload.idempotency_key or x_idempotency_key or "").strip() or None
    if idempotency_key and len(idempotency_key) < 8:
        raise HTTPException(status_code=400, detail="idempotency_key must be at least 8 characters")

    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly")
        if payload.student_id != current_user.student_id:
            raise HTTPException(status_code=403, detail="Students can only place orders for themselves")
        _enforce_order_rate_limit(payload.student_id)
        if payload.location_latitude is None or payload.location_longitude is None:
            raise HTTPException(
                status_code=400,
                detail="Location access is required. Enable location and retry inside LPU campus.",
            )
        location_allowed, location_message, _ = _evaluate_location_gate(
            latitude=payload.location_latitude,
            longitude=payload.location_longitude,
            accuracy_m=payload.location_accuracy_m,
        )
        if not location_allowed:
            raise HTTPException(status_code=403, detail=location_message)

    student = db.get(models.Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    slot = db.get(models.BreakSlot, payload.slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Break slot not found")
    _validate_order_time_window(order_date=payload.order_date, slot=slot)

    menu_item = None
    shop = None
    unit_price = 0.0
    legacy_item = db.get(models.FoodItem, payload.food_item_id) if payload.food_item_id else None

    if payload.menu_item_id:
        menu_item = db.get(models.FoodMenuItem, payload.menu_item_id)
        if not menu_item:
            raise HTTPException(status_code=404, detail="Menu item not found")
        if not menu_item.is_active or menu_item.sold_out:
            raise HTTPException(status_code=409, detail="Selected menu item is unavailable")
        if payload.shop_id and payload.shop_id != menu_item.shop_id:
            raise HTTPException(status_code=400, detail="menu_item does not belong to the selected shop")
        shop = db.get(models.FoodShop, menu_item.shop_id)
        if not shop or not shop.is_active:
            raise HTTPException(status_code=409, detail="Shop is not active")
        if menu_item.stock_quantity is not None and menu_item.stock_quantity < payload.quantity:
            raise HTTPException(status_code=409, detail="Insufficient stock for selected menu item")
        legacy_item = _resolve_legacy_food_item_for_menu(
            db,
            menu_item=menu_item,
            explicit_food_item_id=payload.food_item_id,
        )
        unit_price = float(menu_item.base_price)
    else:
        if payload.food_item_id is None:
            raise HTTPException(status_code=400, detail="food_item_id is required when menu_item_id is not provided")
        if not legacy_item:
            raise HTTPException(status_code=404, detail="Food item not found")
        if not legacy_item.is_active:
            raise HTTPException(status_code=400, detail="Food item is inactive")
        if payload.shop_id:
            shop = db.get(models.FoodShop, payload.shop_id)
            if not shop or not shop.is_active:
                raise HTTPException(status_code=409, detail="Shop is not active")
        unit_price = float(legacy_item.price)

    resolved_shop_id = shop.id if shop else payload.shop_id
    resolved_shop_name = (shop.name if shop else (payload.shop_name or "")).strip() or None
    resolved_prep_eta_minutes = _resolve_prep_eta_minutes(menu_item=menu_item, shop=shop)

    if current_user.role == models.UserRole.STUDENT:
        active_statuses = {
            models.FoodOrderStatus.PLACED,
            models.FoodOrderStatus.VERIFIED,
            models.FoodOrderStatus.PREPARING,
            models.FoodOrderStatus.READY,
            models.FoodOrderStatus.OUT_FOR_DELIVERY,
        }
        active_orders = (
            db.query(models.FoodOrder)
            .filter(
                models.FoodOrder.student_id == payload.student_id,
                models.FoodOrder.order_date == payload.order_date,
                models.FoodOrder.status.in_(active_statuses),
            )
            .all()
        )
        normalized_resolved_shop_name = (resolved_shop_name or "").strip().lower()
        for existing in active_orders:
            if resolved_shop_id and existing.shop_id and int(existing.shop_id) != int(resolved_shop_id):
                raise HTTPException(
                    status_code=409,
                    detail="Orders are accepted only from a single shop at a time.",
                )
            existing_shop_name = (existing.shop_name or "").strip().lower()
            if (
                normalized_resolved_shop_name
                and existing_shop_name
                and existing_shop_name != normalized_resolved_shop_name
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Orders are accepted only from a single shop at a time.",
                )

    if idempotency_key:
        existing = (
            db.query(models.FoodOrder)
            .filter(
                models.FoodOrder.student_id == payload.student_id,
                models.FoodOrder.order_date == payload.order_date,
                models.FoodOrder.idempotency_key == idempotency_key,
            )
            .order_by(models.FoodOrder.id.desc())
            .first()
        )
        if existing:
            return existing

    total_price = round(unit_price * payload.quantity, 2)
    now = datetime.utcnow()

    try:
        db.execute(text("BEGIN IMMEDIATE"))
        current_orders_count = (
            db.query(func.count(models.FoodOrder.id))
            .filter(
                models.FoodOrder.slot_id == payload.slot_id,
                models.FoodOrder.order_date == payload.order_date,
                models.FoodOrder.status != models.FoodOrderStatus.CANCELLED,
                models.FoodOrder.status != models.FoodOrderStatus.REJECTED,
                models.FoodOrder.status != models.FoodOrderStatus.REFUNDED,
            )
            .scalar()
            or 0
        )
        if current_orders_count + payload.quantity > slot.max_orders:
            raise HTTPException(
                status_code=409,
                detail="Selected slot is full. Choose another slot to avoid congestion.",
            )

        if menu_item and menu_item.stock_quantity is not None:
            if menu_item.stock_quantity < payload.quantity:
                raise HTTPException(status_code=409, detail="Insufficient stock for selected menu item")
            menu_item.stock_quantity = max(0, menu_item.stock_quantity - payload.quantity)
            if menu_item.stock_quantity == 0:
                menu_item.sold_out = True

        order = models.FoodOrder(
            student_id=payload.student_id,
            shop_id=resolved_shop_id,
            menu_item_id=(menu_item.id if menu_item else payload.menu_item_id),
            food_item_id=legacy_item.id,
            slot_id=payload.slot_id,
            order_date=payload.order_date,
            quantity=payload.quantity,
            unit_price=unit_price,
            total_price=total_price,
            status=models.FoodOrderStatus.PLACED,
            shop_name=resolved_shop_name,
            shop_block=(shop.block if shop else payload.shop_block),
            idempotency_key=idempotency_key,
            payment_status="pending",
            payment_provider=None,
            payment_reference=payload.payment_reference,
            status_note=payload.status_note,
            pickup_point=(payload.pickup_point.strip() if payload.pickup_point else None),
            delivery_eta_minutes=resolved_prep_eta_minutes,
            estimated_ready_at=(now + timedelta(minutes=resolved_prep_eta_minutes)) if resolved_prep_eta_minutes else None,
            location_verified=(payload.location_latitude is not None and payload.location_longitude is not None),
            location_latitude=payload.location_latitude,
            location_longitude=payload.location_longitude,
            location_accuracy_m=payload.location_accuracy_m,
            last_location_verified_at=now if payload.location_latitude is not None else None,
            last_status_updated_at=now,
        )
        db.add(order)
        db.flush()
        _record_order_audit(
            db,
            order,
            event_type="order_created",
            actor=current_user,
            from_status=None,
            to_status=order.status.value,
            message=f"Order created for {order.shop_name or 'shop'}",
            payload={"quantity": order.quantity, "total_price": order.total_price},
        )
        _notify_order_status(db, order, f"Order being verified by {order.shop_name or 'shop'}")
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to place food order") from exc

    db.refresh(order)
    _sync_order_document(order, "web-order")
    return order


@router.post("/orders/checkout", response_model=list[schemas.FoodOrderOut], status_code=status.HTTP_201_CREATED)
def create_food_orders_checkout(
    payload: schemas.FoodCheckoutCreate,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.STUDENT)),
):
    _ensure_food_catalog_seeded(db)
    idempotency_key = (payload.idempotency_key or x_idempotency_key or "").strip() or None
    if idempotency_key and len(idempotency_key) < 8:
        raise HTTPException(status_code=400, detail="idempotency_key must be at least 8 characters")

    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly")
        if payload.student_id != current_user.student_id:
            raise HTTPException(status_code=403, detail="Students can only place orders for themselves")
        _enforce_order_rate_limit(payload.student_id)
        if payload.location_latitude is None or payload.location_longitude is None:
            raise HTTPException(
                status_code=400,
                detail="Location access is required. Enable location and retry inside LPU campus.",
            )
        location_allowed, location_message, _ = _evaluate_location_gate(
            latitude=payload.location_latitude,
            longitude=payload.location_longitude,
            accuracy_m=payload.location_accuracy_m,
        )
        if not location_allowed:
            raise HTTPException(status_code=403, detail=location_message)

    student = db.get(models.Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    slot = db.get(models.BreakSlot, payload.slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Break slot not found")
    _validate_order_time_window(order_date=payload.order_date, slot=slot)

    if idempotency_key:
        line_pattern = f"{idempotency_key}:%"
        existing_lines = (
            db.query(models.FoodOrder)
            .filter(
                models.FoodOrder.student_id == payload.student_id,
                models.FoodOrder.order_date == payload.order_date,
                models.FoodOrder.idempotency_key.like(line_pattern),
            )
            .order_by(models.FoodOrder.id.asc())
            .all()
        )
        if existing_lines and len(existing_lines) >= len(payload.items):
            return existing_lines[: len(payload.items)]

    resolved_shop_id = int(payload.shop_id) if payload.shop_id else None
    line_rows: list[tuple[int, schemas.FoodCheckoutItemCreate, models.FoodMenuItem]] = []
    menu_totals: dict[int, int] = {}
    menu_by_id: dict[int, models.FoodMenuItem] = {}

    for line_index, line in enumerate(payload.items):
        menu_item = db.get(models.FoodMenuItem, line.menu_item_id)
        if not menu_item:
            raise HTTPException(status_code=404, detail=f"Menu item not found: {line.menu_item_id}")
        if not menu_item.is_active or menu_item.sold_out:
            raise HTTPException(status_code=409, detail=f"Selected menu item is unavailable: {line.menu_item_id}")
        if resolved_shop_id and int(menu_item.shop_id) != int(resolved_shop_id):
            raise HTTPException(
                status_code=409,
                detail="Orders are accepted only from a single shop at a time.",
            )
        if resolved_shop_id is None:
            resolved_shop_id = int(menu_item.shop_id)
        menu_totals[menu_item.id] = int(menu_totals.get(menu_item.id, 0) + int(line.quantity))
        menu_by_id[menu_item.id] = menu_item
        line_rows.append((line_index, line, menu_item))

    if not resolved_shop_id:
        raise HTTPException(status_code=400, detail="Unable to resolve shop for checkout")

    shop = db.get(models.FoodShop, resolved_shop_id)
    if not shop or not shop.is_active:
        raise HTTPException(status_code=409, detail="Shop is not active")
    resolved_shop_name = shop.name.strip() or (payload.shop_name or "").strip() or None

    if current_user.role == models.UserRole.STUDENT:
        active_statuses = {
            models.FoodOrderStatus.PLACED,
            models.FoodOrderStatus.VERIFIED,
            models.FoodOrderStatus.PREPARING,
            models.FoodOrderStatus.READY,
            models.FoodOrderStatus.OUT_FOR_DELIVERY,
        }
        active_orders = (
            db.query(models.FoodOrder)
            .filter(
                models.FoodOrder.student_id == payload.student_id,
                models.FoodOrder.order_date == payload.order_date,
                models.FoodOrder.status.in_(active_statuses),
            )
            .all()
        )
        normalized_resolved_shop_name = (resolved_shop_name or "").strip().lower()
        for existing in active_orders:
            if existing.shop_id and int(existing.shop_id) != int(resolved_shop_id):
                raise HTTPException(
                    status_code=409,
                    detail="Orders are accepted only from a single shop at a time.",
                )
            existing_shop_name = (existing.shop_name or "").strip().lower()
            if (
                normalized_resolved_shop_name
                and existing_shop_name
                and existing_shop_name != normalized_resolved_shop_name
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Orders are accepted only from a single shop at a time.",
                )

    total_cart_quantity = sum(int(qty) for qty in menu_totals.values())
    now = datetime.utcnow()
    created_orders: list[models.FoodOrder] = []

    try:
        db.execute(text("BEGIN IMMEDIATE"))
        current_orders_count = (
            db.query(func.count(models.FoodOrder.id))
            .filter(
                models.FoodOrder.slot_id == payload.slot_id,
                models.FoodOrder.order_date == payload.order_date,
                models.FoodOrder.status != models.FoodOrderStatus.CANCELLED,
                models.FoodOrder.status != models.FoodOrderStatus.REJECTED,
                models.FoodOrder.status != models.FoodOrderStatus.REFUNDED,
            )
            .scalar()
            or 0
        )
        if current_orders_count + total_cart_quantity > slot.max_orders:
            raise HTTPException(
                status_code=409,
                detail="Selected slot is full. Choose another slot to avoid congestion.",
            )

        for menu_item_id, required_qty in menu_totals.items():
            menu_item = menu_by_id[menu_item_id]
            db.refresh(menu_item)
            if not menu_item.is_active or menu_item.sold_out:
                raise HTTPException(status_code=409, detail=f"Selected menu item is unavailable: {menu_item.id}")
            if menu_item.stock_quantity is not None and menu_item.stock_quantity < required_qty:
                raise HTTPException(status_code=409, detail=f"Insufficient stock for menu item: {menu_item.id}")
            if menu_item.stock_quantity is not None:
                menu_item.stock_quantity = max(0, int(menu_item.stock_quantity - required_qty))
                if menu_item.stock_quantity == 0:
                    menu_item.sold_out = True

        for line_index, line, menu_item in line_rows:
            legacy_item = _resolve_legacy_food_item_for_menu(
                db,
                menu_item=menu_item,
                explicit_food_item_id=line.food_item_id,
            )
            unit_price = float(menu_item.base_price)
            total_price = round(unit_price * int(line.quantity), 2)
            prep_eta = _resolve_prep_eta_minutes(menu_item=menu_item, shop=shop)
            line_idempotency_key = f"{idempotency_key}:{line_index}" if idempotency_key else None
            line_status_note = (line.status_note or "").strip() or None

            order = models.FoodOrder(
                student_id=payload.student_id,
                shop_id=resolved_shop_id,
                menu_item_id=menu_item.id,
                food_item_id=legacy_item.id,
                slot_id=payload.slot_id,
                order_date=payload.order_date,
                quantity=int(line.quantity),
                unit_price=unit_price,
                total_price=total_price,
                status=models.FoodOrderStatus.PLACED,
                shop_name=resolved_shop_name,
                shop_block=(shop.block if shop else payload.shop_block),
                idempotency_key=line_idempotency_key,
                payment_status="pending",
                payment_provider=None,
                payment_reference=None,
                status_note=line_status_note,
                pickup_point=(payload.pickup_point.strip() if payload.pickup_point else None),
                delivery_eta_minutes=prep_eta,
                estimated_ready_at=(now + timedelta(minutes=prep_eta)) if prep_eta else None,
                location_verified=(payload.location_latitude is not None and payload.location_longitude is not None),
                location_latitude=payload.location_latitude,
                location_longitude=payload.location_longitude,
                location_accuracy_m=payload.location_accuracy_m,
                last_location_verified_at=now if payload.location_latitude is not None else None,
                last_status_updated_at=now,
            )
            db.add(order)
            db.flush()
            _record_order_audit(
                db,
                order,
                event_type="order_created",
                actor=current_user,
                from_status=None,
                to_status=order.status.value,
                message=f"Order created for {order.shop_name or 'shop'}",
                payload={
                    "quantity": order.quantity,
                    "total_price": order.total_price,
                    "bulk_checkout": True,
                    "line_index": line_index,
                },
            )
            _notify_order_status(db, order, f"Order being verified by {order.shop_name or 'shop'}")
            created_orders.append(order)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to place food order") from exc

    for order in created_orders:
        db.refresh(order)
        _sync_order_document(order, "checkout-bulk")
    return created_orders


@router.get("/orders", response_model=list[schemas.FoodOrderOut])
def list_orders(
    order_date: date | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER)
    ),
):
    mongo_rows = _list_orders_from_mongo(order_date=order_date, limit=limit, current_user=current_user)
    if mongo_rows is not None:
        return mongo_rows

    query = db.query(models.FoodOrder)
    if order_date:
        query = query.filter(models.FoodOrder.order_date == order_date)

    query = _scope_order_query_for_user(query, db, current_user)

    query = query.order_by(models.FoodOrder.created_at.desc())
    if limit:
        query = query.limit(limit)
    rows = query.all()
    changed = False
    for order in rows:
        if _enforce_order_timeout(order):
            changed = True
            _record_order_audit(
                db,
                order,
                event_type="order_timeout",
                actor=None,
                from_status=models.FoodOrderStatus.PLACED.value,
                to_status=models.FoodOrderStatus.CANCELLED.value,
                message="Order auto-cancelled due to verification timeout",
            )
            _notify_order_status(db, order, "Order cancelled due to timeout. Please place a fresh order.")
    if changed:
        db.commit()
    for order in rows:
        _sync_order_document(order, "orders-list-read")
    return rows


@router.post("/orders/{order_id}/cancel", response_model=schemas.FoodOrderOut)
def cancel_order(
    order_id: int,
    reason: str | None = Query(default=None, max_length=240),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.STUDENT)),
):
    order = db.get(models.FoodOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id or order.student_id != current_user.student_id:
            raise HTTPException(status_code=403, detail="Students can cancel only their own orders")
        age_minutes = (datetime.utcnow() - order.created_at).total_seconds() / 60.0
        if age_minutes > _order_cancel_window_minutes():
            raise HTTPException(status_code=409, detail="Cancel window expired for this order")
        if order.status not in {
            models.FoodOrderStatus.PLACED,
            models.FoodOrderStatus.VERIFIED,
            models.FoodOrderStatus.PREPARING,
        }:
            raise HTTPException(status_code=409, detail=f"Order cannot be cancelled in '{order.status.value}' state")

    previous = order.status
    _apply_status_transition(order, models.FoodOrderStatus.CANCELLED, note=reason)
    order.cancel_reason = reason or "cancelled_by_user"
    _record_order_audit(
        db,
        order,
        event_type="order_cancelled",
        actor=current_user,
        from_status=previous.value,
        to_status=order.status.value,
        message=order.cancel_reason,
    )
    _notify_order_status(db, order, "Order cancelled.")
    db.commit()
    db.refresh(order)
    _sync_order_document(order, "order-cancel")
    return order


@router.post("/orders/{order_id}/confirm-delivery", response_model=schemas.FoodOrderOut)
def confirm_order_delivery(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    order = db.get(models.FoodOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not current_user.student_id or order.student_id != current_user.student_id:
        raise HTTPException(status_code=403, detail="Cannot confirm delivery for another student's order")
    if order.status == models.FoodOrderStatus.DELIVERED:
        return order
    if order.status != models.FoodOrderStatus.VERIFIED:
        raise HTTPException(status_code=409, detail="Manual delivery confirmation is allowed only for verified orders")
    if str(order.payment_status or "").strip().lower() not in {"paid", "captured"}:
        raise HTTPException(status_code=409, detail="Only paid orders can be marked delivered")

    previous = order.status
    _apply_status_transition(order, models.FoodOrderStatus.DELIVERED, note="Delivery confirmed by student")
    _record_order_audit(
        db,
        order,
        event_type="order_delivery_confirmed_student",
        actor=current_user,
        from_status=previous.value,
        to_status=order.status.value,
        message="Delivery manually confirmed by student",
        payload={"confirmed_by_student": True},
    )
    _notify_order_status(db, order, "Delivery confirmed. Please rate your order.")
    db.commit()
    db.refresh(order)
    _sync_order_document(order, "order-delivery-confirm")
    return order


@router.patch("/orders/{order_id}/rating", response_model=schemas.FoodOrderOut)
def update_order_rating(
    order_id: int,
    payload: schemas.FoodOrderRatingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    order = db.get(models.FoodOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not current_user.student_id or order.student_id != current_user.student_id:
        raise HTTPException(status_code=403, detail="Cannot rate another student's order")
    if order.status != models.FoodOrderStatus.DELIVERED:
        raise HTTPException(status_code=409, detail="Only delivered orders can be rated")
    if order.rating_locked_at:
        raise HTTPException(status_code=409, detail="Rating already confirmed and locked for this order")

    previous_rating = order.rating_stars
    shop_rating_before: float | None = None
    shop_rating_after: float | None = None
    shop_rating_count = 0
    requested_stars = int(payload.stars or 0)
    if requested_stars <= 0:
        raise HTTPException(status_code=422, detail="Select a rating between 1 and 5 stars")
    if not bool(payload.confirm_final):
        raise HTTPException(status_code=422, detail="Confirm rating before submitting")
    rating_time = datetime.utcnow()
    order.rating_stars = requested_stars
    order.rating_comment = (str(payload.comment or "").strip() or None)
    order.rated_at = rating_time
    order.rating_locked_at = rating_time

    if order.shop_id:
        shop_row = db.get(models.FoodShop, int(order.shop_id))
        if shop_row:
            shop_rating_before = round(float(shop_row.rating or 0.0), 2)
        refreshed_shop, shop_rating_count = _refresh_shop_rating_from_orders(db, order.shop_id)
        if refreshed_shop:
            shop_rating_after = round(float(refreshed_shop.rating or 0.0), 2)

    _record_order_audit(
        db,
        order,
        event_type="order_rating_updated",
        actor=current_user,
        from_status=order.status.value,
        to_status=order.status.value,
        message="Order rating updated",
        payload={
            "previous_rating": previous_rating,
            "rating_stars": order.rating_stars,
            "rating_comment": order.rating_comment,
            "confirm_final": bool(payload.confirm_final),
            "rating_locked_at": order.rating_locked_at,
            "shop_rating_before": shop_rating_before,
            "shop_rating_after": shop_rating_after,
            "shop_rating_count": shop_rating_count,
        },
    )
    mirror_event(
        "food.order.rating.updated",
        {
            "order_id": order.id,
            "student_id": order.student_id,
            "rating_stars": order.rating_stars,
            "has_comment": bool(order.rating_comment),
        },
        source="food-router",
        actor={"id": current_user.id, "email": current_user.email, "role": current_user.role.value},
    )
    db.commit()
    db.refresh(order)
    if order.shop_id:
        shop = db.get(models.FoodShop, int(order.shop_id))
        if shop:
            mirror_document(
                "food_shops",
                {
                    "id": shop.id,
                    "shop_id": shop.id,
                    "name": shop.name,
                    "block": shop.block,
                    "owner_user_id": shop.owner_user_id,
                    "is_active": shop.is_active,
                    "is_popular": shop.is_popular,
                    "rating": shop.rating,
                    "average_prep_minutes": shop.average_prep_minutes,
                    "updated_at": shop.updated_at,
                    "source": "shop-rating-refresh",
                },
                upsert_filter={"shop_id": shop.id},
            )
            mirror_event(
                "food.shop.rating.updated",
                {
                    "shop_id": shop.id,
                    "shop_name": shop.name,
                    "rating": shop.rating,
                    "rating_count": shop_rating_count,
                    "trigger_order_id": order.id,
                },
                source="food-router",
                actor={"id": current_user.id, "email": current_user.email, "role": current_user.role.value},
            )
    _sync_order_document(order, "order-rating")
    return order


@router.get("/orders/{order_id}/audit", response_model=list[schemas.FoodOrderAuditOut])
def list_order_audit(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER)
    ),
):
    order = db.get(models.FoodOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role == models.UserRole.FACULTY:
        raise HTTPException(status_code=403, detail="Faculty accounts cannot view per-order audit logs")
    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id or order.student_id != current_user.student_id:
            raise HTTPException(status_code=403, detail="Cannot view audit for another student's order")
    if current_user.role == models.UserRole.OWNER:
        shop = db.get(models.FoodShop, order.shop_id) if order.shop_id else None
        if not shop or shop.owner_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions for this shop order")
    rows = (
        db.query(models.FoodOrderAudit)
        .filter(models.FoodOrderAudit.order_id == order_id)
        .order_by(models.FoodOrderAudit.created_at.desc())
        .all()
    )
    return rows


@router.post("/payments/intent", response_model=schemas.FoodPaymentIntentOut)
def create_payment_intent(
    payload: schemas.FoodPaymentIntentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.STUDENT)),
):
    orders = db.query(models.FoodOrder).filter(models.FoodOrder.id.in_(payload.order_ids)).all()
    if len(orders) != len(payload.order_ids):
        raise HTTPException(status_code=404, detail="Some orders were not found")
    if current_user.role == models.UserRole.STUDENT:
        if not current_user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked correctly")
        if any(order.student_id != current_user.student_id for order in orders):
            raise HTTPException(status_code=403, detail="Cannot create payment for another student's order")

    if any(_is_order_final(order.status) for order in orders):
        raise HTTPException(status_code=409, detail="Payment cannot be created for finalized orders")

    subtotal_amount = round(sum(float(order.total_price or 0) for order in orders), 2)
    if subtotal_amount <= 0:
        raise HTTPException(status_code=409, detail="Invalid order amount for payment")
    delivery_fee = round(_delivery_fee_inr(), 2)
    platform_fee = round(_platform_fee_inr(), 2)
    amount = round(subtotal_amount + delivery_fee + platform_fee, 2)

    local_reference = f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4).upper()}"
    provider_order_id = None
    metadata: dict = {
        "receipt": local_reference,
        "order_ids": [order.id for order in orders],
        "subtotal_amount": subtotal_amount,
        "delivery_fee": delivery_fee,
        "platform_fee": platform_fee,
        "total_amount": amount,
    }

    if payload.provider == "razorpay":
        rzp = _get_razorpay_client()
        if not rzp:
            raise HTTPException(status_code=500, detail="Razorpay is not configured")
        rzp_order = rzp.order.create({
            "amount": int(amount * 100),
            "currency": "INR",
            "receipt": local_reference,
            "notes": {
                "source": "lpu-smart-campus",
                "student_id": str(orders[0].student_id),
                "subtotal_inr": str(subtotal_amount),
                "delivery_fee_inr": str(delivery_fee),
                "platform_fee_inr": str(platform_fee),
            },
        })
        provider_order_id = str(rzp_order.get("id") or "")
        if not provider_order_id:
            raise HTTPException(status_code=500, detail="Razorpay order id was not returned")
        metadata["provider_order_payload"] = rzp_order

    reference = provider_order_id or local_reference

    payment = models.FoodPayment(
        student_id=orders[0].student_id,
        amount=amount,
        currency="INR",
        provider=payload.provider,
        payment_reference=reference,
        provider_order_id=provider_order_id,
        order_state="created",
        payment_state="created",
        status="created",
        metadata_json=json.dumps(metadata),
        order_ids_json=json.dumps([order.id for order in orders]),
    )
    db.add(payment)
    db.flush()
    for order in orders:
        order.payment_status = "created"
        order.payment_provider = payload.provider
        order.payment_reference = reference
        _record_order_audit(
            db,
            order,
            event_type="payment_intent_created",
            actor=current_user,
            from_status=order.status.value,
            to_status=order.status.value,
                message=f"Payment created ({reference})",
                payload={
                    "amount": amount,
                    "subtotal_amount": subtotal_amount,
                    "delivery_fee": delivery_fee,
                    "platform_fee": platform_fee,
                    "provider": payload.provider,
                    "payment_state": "created",
                    "order_state": "created",
                },
            )
    db.commit()
    mirror_document(
        "food_payments",
        {
            "payment_id": payment.id,
            "payment_reference": reference,
            "provider_order_id": provider_order_id,
            "student_id": payment.student_id,
            "amount": payment.amount,
            "subtotal_amount": subtotal_amount,
            "delivery_fee": delivery_fee,
            "platform_fee": platform_fee,
            "currency": payment.currency,
            "provider": payment.provider,
            "status": payment.status,
            "order_state": payment.order_state,
            "payment_state": payment.payment_state,
            "attempt_count": payment.attempt_count,
            "order_ids": payload.order_ids,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
            "source": "payment-intent",
        },
        upsert_filter={"payment_reference": reference},
    )
    return schemas.FoodPaymentIntentOut(
        payment_reference=reference,
        provider_order_id=provider_order_id,
        provider=payload.provider,
        status="created",
        amount=amount,
        subtotal_amount=subtotal_amount,
        delivery_fee=delivery_fee,
        platform_fee=platform_fee,
        currency="INR",
        order_ids=payload.order_ids,
    )


@router.post("/payments/webhook", response_model=schemas.MessageResponse)
async def payment_webhook(
    request: Request,
    x_webhook_token: str | None = Header(default=None, alias="X-Webhook-Token"),
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: str | None = Header(default=None, alias="X-Razorpay-Event-Id"),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(status_code=400, detail="Webhook payload is required")
    try:
        incoming_payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload JSON") from exc
    if not isinstance(incoming_payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object")

    provider = str(
        incoming_payload.get("provider")
        or ("razorpay" if x_razorpay_signature else "sandbox")
    ).strip().lower() or "sandbox"
    expected = _payment_webhook_token()
    if provider != "razorpay":
        if expected and x_webhook_token != expected:
            raise HTTPException(status_code=401, detail="Invalid webhook token")
    elif expected and x_webhook_token and x_webhook_token != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    payment_reference = str(incoming_payload.get("payment_reference") or "").strip()
    webhook_status = str(incoming_payload.get("status") or "").strip().lower()
    webhook_payload = incoming_payload.get("payload") if isinstance(incoming_payload.get("payload"), dict) else {}
    provider_payment_id: str | None = None
    provider_signature: str | None = None

    if provider == "razorpay":
        secret = _razorpay_webhook_secret()
        if not secret:
            raise HTTPException(status_code=500, detail="Razorpay webhook secret is not configured")
        incoming_signature = str(x_razorpay_signature or "").strip()
        if not incoming_signature:
            raise HTTPException(status_code=401, detail="Missing Razorpay webhook signature")
        if not _verify_razorpay_webhook_signature(secret=secret, raw_body=raw_body, incoming_signature=incoming_signature):
            raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")

        custom_payment_id = str(
            webhook_payload.get("razorpay_payment_id")
            or webhook_payload.get("payment_id")
            or ""
        ).strip() or None
        custom_signature = str(
            webhook_payload.get("razorpay_signature")
            or webhook_payload.get("signature")
            or incoming_signature
            or ""
        ).strip() or None

        native_order_id, native_payment_id, native_status, native_payload = _extract_razorpay_webhook_fields(incoming_payload)
        if not payment_reference:
            payment_reference = native_order_id or ""
        if not webhook_status:
            webhook_status = str(native_status or "").strip().lower()
        if not webhook_payload:
            webhook_payload = native_payload
        provider_payment_id = custom_payment_id or native_payment_id
        provider_signature = custom_signature
    elif isinstance(webhook_payload, dict):
        provider_payment_id = str(
            webhook_payload.get("payment_id")
            or webhook_payload.get("provider_payment_id")
            or ""
        ).strip() or None
        provider_signature = str(
            webhook_payload.get("signature")
            or ""
        ).strip() or None

    if not payment_reference:
        raise HTTPException(status_code=400, detail="payment_reference is required in webhook payload")
    if not webhook_status:
        raise HTTPException(status_code=400, detail="status is required in webhook payload")

    fingerprint_seed = raw_body or json.dumps(incoming_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    fingerprint = hashlib.sha256(fingerprint_seed).hexdigest()
    event_id = (
        str(x_razorpay_event_id or "").strip()
        or str(webhook_payload.get("event_id") or webhook_payload.get("event") or "").strip()
        or str(incoming_payload.get("event") or "").strip()
        or None
    )
    mongo_db = _mongo_db_or_503()
    replayed = _register_payment_webhook_event(
        mongo_db=mongo_db,
        provider=provider,
        event_id=event_id,
        fingerprint=fingerprint,
        signature=(x_razorpay_signature or webhook_payload.get("razorpay_signature")),
        payload=incoming_payload,
    )
    if replayed:
        return schemas.MessageResponse(message="Webhook already processed")

    payment = (
        db.query(models.FoodPayment)
        .filter(
            (models.FoodPayment.payment_reference == payment_reference)
            | (models.FoodPayment.provider_order_id == payment_reference)
        )
        .first()
    )
    if not payment and provider_payment_id:
        payment = (
            db.query(models.FoodPayment)
            .filter(models.FoodPayment.provider_payment_id == provider_payment_id)
            .first()
        )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment reference not found")

    next_order_state, next_payment_state, next_status = _normalize_webhook_payment_state(webhook_status)
    if _is_payment_paid(payment) and next_status != "paid":
        return schemas.MessageResponse(message="Webhook ignored: payment already captured")

    payment.provider = provider
    payment.webhook_payload_json = json.dumps(webhook_payload or {})
    payment.updated_at = datetime.utcnow()
    if not provider_signature and x_razorpay_signature:
        provider_signature = str(x_razorpay_signature).strip() or None
    no_state_change = (
        str(payment.order_state or "") == next_order_state
        and str(payment.payment_state or "") == next_payment_state
        and str(payment.status or "") == next_status
    )
    same_provider_ids = (not provider_payment_id or str(payment.provider_payment_id or "") == provider_payment_id)
    if no_state_change and same_provider_ids:
        return schemas.MessageResponse(message="Webhook already processed")

    if provider_payment_id:
        payment.provider_payment_id = provider_payment_id
    if provider_signature:
        payment.provider_signature = provider_signature
    payment.order_state = next_order_state
    payment.payment_state = next_payment_state
    payment.status = next_status
    if next_status == "paid":
        payment.failed_reason = None
        payment.verified_at = datetime.utcnow()
    elif next_status == "failed":
        payment.failed_reason = webhook_status or "payment_failed"

    order_ids = json.loads(payment.order_ids_json or "[]")
    if not isinstance(order_ids, list):
        order_ids = []
    orders = db.query(models.FoodOrder).filter(models.FoodOrder.id.in_(order_ids)).all()
    paid = next_status == "paid"
    orders_changed: list[tuple[models.FoodOrder, models.FoodOrderStatus, str, str]] = []
    for order in orders:
        previous_status = order.status
        previous_payment_status = str(order.payment_status or "")
        previous_payment_ref = str(order.payment_reference or "")

        if paid:
            order.payment_status = "paid"
            order.payment_provider = provider
            order.payment_reference = provider_payment_id or payment_reference
            if order.status == models.FoodOrderStatus.PLACED:
                _apply_status_transition(order, models.FoodOrderStatus.VERIFIED, note="Payment verified")
        elif next_status == "failed":
            if not str(order.payment_status or "").lower() == "paid":
                order.payment_status = "failed"
                order.payment_provider = provider
                order.payment_reference = provider_payment_id or payment_reference
        else:
            if not str(order.payment_status or "").lower() == "paid":
                order.payment_status = "attempted"
                order.payment_provider = provider
                order.payment_reference = provider_payment_id or payment_reference

        order_mutated = (
            previous_status != order.status
            or previous_payment_status != str(order.payment_status or "")
            or previous_payment_ref != str(order.payment_reference or "")
        )
        if not order_mutated:
            continue
        orders_changed.append((order, previous_status, previous_payment_status, previous_payment_ref))

    for order, previous_status, previous_payment_status, previous_payment_ref in orders_changed:
        if paid:
            _notify_order_status(db, order, "Order verified.")
        elif next_status == "failed":
            _notify_order_status(db, order, "Payment failed. Please retry checkout.")
        _record_order_audit(
            db,
            order,
            event_type="payment_webhook",
            actor=None,
            from_status=previous_status.value,
            to_status=order.status.value,
            message=f"Payment webhook: {payment.payment_state}",
            payload={
                "provider": provider,
                "payment_reference": payment_reference,
                "provider_payment_id": provider_payment_id,
                "provider_signature": bool(provider_signature),
                "order_state": payment.order_state,
                "payment_state": payment.payment_state,
                "event_id": event_id,
                "previous_payment_status": previous_payment_status,
                "previous_payment_reference": previous_payment_ref,
            },
        )

    db.commit()
    for order, _, _, _ in orders_changed:
        _sync_order_document(order, "payment-webhook")
    if paid and payment.student_id:
        _try_clear_food_cart(student_id=int(payment.student_id))
    mirror_document(
        "food_payments",
        {
            "payment_reference": payment_reference,
            "provider": provider,
            "status": payment.status,
            "order_state": payment.order_state,
            "payment_state": payment.payment_state,
            "provider_order_id": payment.provider_order_id,
            "provider_payment_id": payment.provider_payment_id,
            "provider_signature": payment.provider_signature,
            "failed_reason": payment.failed_reason,
            "attempt_count": payment.attempt_count,
            "order_ids": order_ids,
            "verified_at": payment.verified_at,
            "updated_at": payment.updated_at,
            "event_id": event_id,
            "source": "payment-webhook",
        },
        upsert_filter={"payment_reference": payment_reference},
    )
    return schemas.MessageResponse(message="Webhook processed")


@router.get("/demand", response_model=list[schemas.SlotDemand])
def get_slot_demand(
    order_date: date = Query(...),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER)
    ),
):
    slots = _query_food_slots(db)
    response: list[schemas.SlotDemand] = []

    for slot in slots:
        order_count = (
            db.query(func.count(models.FoodOrder.id))
            .filter(
                models.FoodOrder.slot_id == slot.id,
                models.FoodOrder.order_date == order_date,
                models.FoodOrder.status != models.FoodOrderStatus.CANCELLED,
                models.FoodOrder.status != models.FoodOrderStatus.REJECTED,
            )
            .scalar()
            or 0
        )
        utilization = (order_count / slot.max_orders * 100.0) if slot.max_orders else 0.0
        response.append(
            schemas.SlotDemand(
                slot_id=slot.id,
                slot_label=slot.label,
                orders=order_count,
                capacity=slot.max_orders,
                utilization_percent=round(utilization, 2),
            )
        )

    return sorted(response, key=lambda x: x.orders, reverse=True)


@router.get("/demand/live", response_model=schemas.SlotDemandLiveOut)
def get_slot_demand_live_signal(
    order_date: date = Query(...),
    window_minutes: int = Query(default=2, ge=1, le=15),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER)
    ),
):
    slots = _query_food_slots(db)
    slot_label_by_id = {int(slot.id): str(slot.label) for slot in slots}

    base_order_query = db.query(models.FoodOrder).filter(models.FoodOrder.order_date == order_date)
    if current_user.role == models.UserRole.OWNER:
        base_order_query = _order_visible_to_owner_filter(base_order_query, db, current_user.id)

    active_orders = (
        base_order_query
        .filter(
            ~models.FoodOrder.status.in_(
                [
                    models.FoodOrderStatus.CANCELLED,
                    models.FoodOrderStatus.REJECTED,
                    models.FoodOrderStatus.DELIVERED,
                    models.FoodOrderStatus.COLLECTED,
                    models.FoodOrderStatus.REFUNDED,
                ]
            )
        )
        .count()
    )

    slot_count_rows = (
        base_order_query
        .with_entities(
            models.FoodOrder.slot_id.label("slot_id"),
            func.count(models.FoodOrder.id).label("order_count"),
        )
        .filter(
            models.FoodOrder.status != models.FoodOrderStatus.CANCELLED,
            models.FoodOrder.status != models.FoodOrderStatus.REJECTED,
        )
        .group_by(models.FoodOrder.slot_id)
        .all()
    )

    hottest_slot_label: str | None = None
    hottest_slot_orders = 0
    if slot_count_rows:
        hottest_row = max(slot_count_rows, key=lambda row: int(row.order_count or 0))
        hottest_slot_orders = int(hottest_row.order_count or 0)
        hottest_slot_id = int(hottest_row.slot_id or 0)
        if hottest_slot_id:
            hottest_slot_label = slot_label_by_id.get(hottest_slot_id, f"Slot #{hottest_slot_id}")

    window_start = datetime.utcnow() - timedelta(minutes=window_minutes)
    audit_query = (
        db.query(
            models.FoodOrder.slot_id.label("slot_id"),
            models.FoodOrderAudit.event_type.label("event_type"),
            func.count(models.FoodOrderAudit.id).label("event_count"),
        )
        .join(models.FoodOrder, models.FoodOrder.id == models.FoodOrderAudit.order_id)
        .filter(
            models.FoodOrder.order_date == order_date,
            models.FoodOrderAudit.created_at >= window_start,
        )
    )
    if current_user.role == models.UserRole.OWNER:
        audit_query = _order_visible_to_owner_filter(audit_query, db, current_user.id)
    audit_rows = audit_query.group_by(models.FoodOrder.slot_id, models.FoodOrderAudit.event_type).all()

    orders_last_window = 0
    status_updates_last_window = 0
    payment_events_last_window = 0
    pulse_bucket_by_slot: dict[int, dict[str, int]] = {}

    for row in audit_rows:
        slot_id = int(row.slot_id or 0)
        if slot_id <= 0:
            continue
        count = int(row.event_count or 0)
        if count <= 0:
            continue

        bucket = pulse_bucket_by_slot.setdefault(
            slot_id,
            {
                "event_count": 0,
                "created_count": 0,
                "status_count": 0,
                "payment_count": 0,
            },
        )
        bucket["event_count"] += count

        event_type = str(row.event_type or "").strip().lower()
        if event_type == "order_created":
            bucket["created_count"] += count
            orders_last_window += count
        elif event_type.startswith("payment_"):
            bucket["payment_count"] += count
            payment_events_last_window += count
        else:
            bucket["status_count"] += count
            status_updates_last_window += count

    pulses: list[schemas.SlotDemandLivePulse] = []
    sorted_pulses = sorted(
        pulse_bucket_by_slot.items(),
        key=lambda pair: (-int(pair[1]["event_count"]), slot_label_by_id.get(pair[0], f"Slot #{pair[0]}")),
    )
    for slot_id, bucket in sorted_pulses:
        slot_label = slot_label_by_id.get(slot_id, f"Slot #{slot_id}")
        pulses.append(
            schemas.SlotDemandLivePulse(
                slot_id=slot_id,
                slot_label=slot_label,
                event_count=int(bucket["event_count"]),
                created_count=int(bucket["created_count"]),
                status_count=int(bucket["status_count"]),
                payment_count=int(bucket["payment_count"]),
            )
        )

    return schemas.SlotDemandLiveOut(
        order_date=order_date,
        window_minutes=window_minutes,
        synced_at=datetime.utcnow(),
        active_orders=int(active_orders or 0),
        orders_last_window=int(orders_last_window),
        status_updates_last_window=int(status_updates_last_window),
        payment_events_last_window=int(payment_events_last_window),
        hottest_slot_label=hottest_slot_label,
        hottest_slot_orders=int(hottest_slot_orders),
        pulses=pulses,
    )


@router.get("/peak-times", response_model=list[schemas.PeakTimePrediction])
def get_peak_times(
    lookback_days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.STUDENT, models.UserRole.OWNER)
    ),
):
    today = date.today()
    start_date = today - timedelta(days=lookback_days - 1)

    slots = _query_food_slots(db)
    slot_day_counts = (
        db.query(
            models.FoodOrder.slot_id,
            models.FoodOrder.order_date,
            func.count(models.FoodOrder.id).label("order_count"),
        )
        .filter(
            models.FoodOrder.order_date >= start_date,
            models.FoodOrder.order_date <= today,
            models.FoodOrder.status != models.FoodOrderStatus.CANCELLED,
            models.FoodOrder.status != models.FoodOrderStatus.REJECTED,
        )
        .group_by(models.FoodOrder.slot_id, models.FoodOrder.order_date)
        .all()
    )

    count_map: dict[int, dict[date, int]] = {}
    for row in slot_day_counts:
        count_map.setdefault(row.slot_id, {})[row.order_date] = row.order_count

    predictions: list[schemas.PeakTimePrediction] = []
    for slot in slots:
        daily_counts = count_map.get(slot.id, {})
        average_orders = sum(daily_counts.values()) / lookback_days
        utilization_ratio = (average_orders / slot.max_orders) if slot.max_orders else 0

        if utilization_ratio >= 0.8:
            rush_level = "high"
        elif utilization_ratio >= 0.5:
            rush_level = "medium"
        else:
            rush_level = "low"

        predictions.append(
            schemas.PeakTimePrediction(
                slot_id=slot.id,
                slot_label=slot.label,
                average_orders=round(average_orders, 2),
                predicted_rush_level=rush_level,
            )
        )

    return sorted(predictions, key=lambda x: x.average_orders, reverse=True)


@router.patch("/orders/{order_id}/status", response_model=schemas.FoodOrderOut)
def update_order_status(
    order_id: int,
    payload: schemas.FoodOrderStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.OWNER)),
):
    order = db.get(models.FoodOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role == models.UserRole.OWNER:
        if not order.shop_id:
            raise HTTPException(status_code=403, detail="Owner can only update assigned shop orders")
        shop = db.get(models.FoodShop, order.shop_id)
        if not shop or shop.owner_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions for this shop order")

    if not _status_transition_allowed(order.status, payload.status):
        raise HTTPException(
            status_code=409,
            detail=f"Invalid status transition from '{order.status.value}' to '{payload.status.value}'",
        )

    previous = order.status
    if payload.assigned_runner is not None:
        order.assigned_runner = payload.assigned_runner.strip() or None
    if payload.pickup_point is not None:
        order.pickup_point = payload.pickup_point.strip() or None
    if payload.delivery_eta_minutes is not None:
        order.delivery_eta_minutes = int(payload.delivery_eta_minutes)
    _apply_status_transition(order, payload.status, note=payload.status_note)
    _record_order_audit(
        db,
        order,
        event_type="status_updated",
        actor=current_user,
        from_status=previous.value,
        to_status=order.status.value,
        message=payload.status_note or f"Status changed to {order.status.value}",
        payload={
            "assigned_runner": order.assigned_runner,
            "pickup_point": order.pickup_point,
            "delivery_eta_minutes": order.delivery_eta_minutes,
        },
    )
    status_message_map = {
        models.FoodOrderStatus.PLACED: f"Order being verified by {order.shop_name or 'shop'}",
        models.FoodOrderStatus.VERIFIED: "Order verified",
        models.FoodOrderStatus.PREPARING: "Cooking your meals",
        models.FoodOrderStatus.OUT_FOR_DELIVERY: "Out for delivery",
        models.FoodOrderStatus.DELIVERED: "Delivered",
        models.FoodOrderStatus.CANCELLED: "Order cancelled",
        models.FoodOrderStatus.REJECTED: "Order rejected",
    }
    status_message = status_message_map.get(order.status, f"Order status: {order.status.value}")
    _notify_order_status(db, order, status_message)
    db.commit()
    db.refresh(order)
    _sync_order_document(order, "shop-status-update")
    return order


@router.get("/ops/metrics", response_model=schemas.FoodMetricsOut)
def food_ops_metrics(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.FACULTY, models.UserRole.OWNER)),
):
    today = date.today()
    query = db.query(models.FoodOrder)
    if current_user.role == models.UserRole.OWNER:
        query = _order_visible_to_owner_filter(query, db, current_user.id)

    rows = query.all()
    today_rows = [row for row in rows if row.order_date == today]
    active_orders = sum(1 for row in rows if not _is_order_final(row.status))
    completed_today = sum(
        1
        for row in today_rows
        if row.status in {models.FoodOrderStatus.DELIVERED, models.FoodOrderStatus.COLLECTED}
    )
    cancelled_today = sum(1 for row in today_rows if row.status == models.FoodOrderStatus.CANCELLED)
    rejection_today = sum(1 for row in today_rows if row.status == models.FoodOrderStatus.REJECTED)

    prep_minutes: list[float] = []
    for row in rows:
        if not row.preparing_at:
            continue
        end_stamp = row.out_for_delivery_at or row.delivered_at or row.estimated_ready_at
        if not end_stamp:
            continue
        duration = (end_stamp - row.preparing_at).total_seconds() / 60.0
        if duration >= 0:
            prep_minutes.append(duration)

    funnel: dict[str, int] = {}
    for status_value in models.FoodOrderStatus:
        funnel[status_value.value] = sum(1 for row in rows if row.status == status_value)

    return schemas.FoodMetricsOut(
        active_orders=active_orders,
        completed_today=completed_today,
        cancelled_today=cancelled_today,
        rejection_today=rejection_today,
        avg_preparing_minutes=round((sum(prep_minutes) / len(prep_minutes)) if prep_minutes else 0.0, 2),
        funnel=funnel,
        generated_at=datetime.utcnow(),
    )


@router.get("/payments/config", response_model=schemas.RazorpayConfigOut)
def get_payment_config(
    _: CurrentUser = Depends(require_roles(models.UserRole.ADMIN, models.UserRole.STUDENT, models.UserRole.FACULTY, models.UserRole.OWNER)),
):
    key_id = os.getenv("RAZORPAY_KEY_ID", "")
    if not key_id:
        raise HTTPException(status_code=500, detail="Razorpay configuration is missing")
    return schemas.RazorpayConfigOut(key_id=key_id)


@router.get("/payments/recovery", response_model=list[schemas.FoodPaymentRecoveryItemOut])
def list_payment_recovery_candidates(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    if not current_user.student_id:
        raise HTTPException(status_code=403, detail="Student account is not linked correctly")

    rows = (
        db.query(models.FoodPayment)
        .filter(
            models.FoodPayment.student_id == current_user.student_id,
            models.FoodPayment.status.in_(["failed", "attempted", "created"]),
        )
        .order_by(models.FoodPayment.updated_at.desc(), models.FoodPayment.created_at.desc())
        .limit(30)
        .all()
    )

    output: list[schemas.FoodPaymentRecoveryItemOut] = []
    for row in rows:
        order_ids = json.loads(row.order_ids_json or "[]")
        if not isinstance(order_ids, list):
            continue
        order_ids = [int(i) for i in order_ids if isinstance(i, int) or str(i).isdigit()]
        if not order_ids:
            continue
        orders = db.query(models.FoodOrder).filter(models.FoodOrder.id.in_(order_ids)).all()
        if not orders:
            continue
        if all(_is_order_final(order.status) or str(order.payment_status or "").lower() == "paid" for order in orders):
            continue

        output.append(
            schemas.FoodPaymentRecoveryItemOut(
                payment_reference=row.payment_reference,
                provider_order_id=row.provider_order_id,
                status=row.status,
                payment_state=row.payment_state,
                failed_reason=row.failed_reason,
                order_ids=order_ids,
                amount=round(float(row.amount or 0.0), 2),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    return output


@router.post("/payments/verify", response_model=schemas.MessageResponse)
def verify_payment(
    payload: schemas.RazorpayVerifyRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    rzp = _get_razorpay_client()
    if not rzp:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")

    try:
        rzp.utility.verify_payment_signature({
            "razorpay_order_id": payload.razorpay_order_id,
            "razorpay_payment_id": payload.razorpay_payment_id,
            "razorpay_signature": payload.razorpay_signature,
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    payment = (
        db.query(models.FoodPayment)
        .filter(
            (models.FoodPayment.provider_order_id == payload.razorpay_order_id)
            | (models.FoodPayment.payment_reference == payload.razorpay_order_id)
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment reference not found")
    if not current_user.student_id or payment.student_id != current_user.student_id:
        raise HTTPException(status_code=403, detail="Cannot verify payment for another student")

    payment_was_already_paid = _is_payment_paid(payment)
    existing_provider_payment_id = str(payment.provider_payment_id or "").strip()
    incoming_provider_payment_id = str(payload.razorpay_payment_id or "").strip()
    if payment_was_already_paid:
        if existing_provider_payment_id and incoming_provider_payment_id == existing_provider_payment_id:
            return schemas.MessageResponse(message="Payment already verified")
        if not existing_provider_payment_id and incoming_provider_payment_id:
            # Backfill provider references if webhook captured payment first.
            payment.provider_order_id = payload.razorpay_order_id
            payment.provider_payment_id = payload.razorpay_payment_id
            payment.provider_signature = payload.razorpay_signature
            payment.updated_at = datetime.utcnow()
            db.commit()
            mirror_document(
                "food_payments",
                {
                    "payment_reference": payment.payment_reference,
                    "provider": "razorpay",
                    "status": payment.status,
                    "order_state": payment.order_state,
                    "payment_state": payment.payment_state,
                    "provider_order_id": payment.provider_order_id,
                    "provider_payment_id": payment.provider_payment_id,
                    "provider_signature": payment.provider_signature,
                    "attempt_count": payment.attempt_count,
                    "updated_at": payment.updated_at,
                    "source": "payment-verify-backfill",
                },
                upsert_filter={"payment_reference": payment.payment_reference},
            )
            return schemas.MessageResponse(message="Payment already verified")
        raise HTTPException(status_code=409, detail="Payment already captured")

    payment.provider_order_id = payload.razorpay_order_id
    payment.provider_payment_id = payload.razorpay_payment_id
    payment.provider_signature = payload.razorpay_signature
    payment.attempt_count = int(payment.attempt_count or 0) + 1
    payment.order_state = "paid"
    payment.payment_state = "captured"
    payment.provider = "razorpay"
    payment.status = "paid"
    payment.failed_reason = None
    payment.updated_at = datetime.utcnow()
    payment.verified_at = datetime.utcnow()
    payment.webhook_payload_json = json.dumps({
        "razorpay_payment_id": payload.razorpay_payment_id,
        "razorpay_order_id": payload.razorpay_order_id,
    })

    order_ids = json.loads(payment.order_ids_json or "[]")
    if not isinstance(order_ids, list):
        order_ids = []
    orders = db.query(models.FoodOrder).filter(models.FoodOrder.id.in_(order_ids)).all()

    orders_changed: list[tuple[models.FoodOrder, models.FoodOrderStatus, str, str, bool]] = []
    for order in orders:
        previous_status = order.status
        previous_payment_status = str(order.payment_status or "")
        previous_payment_ref = str(order.payment_reference or "")
        transitioned = False

        order.payment_status = "paid"
        order.payment_provider = "razorpay"
        order.payment_reference = payload.razorpay_payment_id
        if order.status == models.FoodOrderStatus.PLACED:
            _apply_status_transition(order, models.FoodOrderStatus.VERIFIED, note="Payment verified via Razorpay")
            transitioned = True
        order_mutated = (
            previous_status != order.status
            or previous_payment_status != str(order.payment_status or "")
            or previous_payment_ref != str(order.payment_reference or "")
        )
        if not order_mutated:
            continue
        orders_changed.append((order, previous_status, previous_payment_status, previous_payment_ref, transitioned))

    for order, previous_status, previous_payment_status, previous_payment_ref, transitioned in orders_changed:
        if transitioned:
            _notify_order_status(db, order, "Order verified.")
        _record_order_audit(
            db,
            order,
            event_type="payment_verified_client",
            actor=current_user,
            from_status=previous_status.value,
            to_status=order.status.value,
            message="Payment verified via client SDK",
            payload={
                "provider": "razorpay",
                "payment_reference": payload.razorpay_payment_id,
                "provider_order_id": payload.razorpay_order_id,
                "order_state": payment.order_state,
                "payment_state": payment.payment_state,
                "previous_payment_status": previous_payment_status,
                "previous_payment_reference": previous_payment_ref,
            },
        )

    db.commit()
    for order, _, _, _, _ in orders_changed:
        _sync_order_document(order, "payment-verify")
    _try_clear_food_cart(student_id=int(payment.student_id), user_id=current_user.id)
    mirror_document(
        "food_payments",
        {
            "payment_reference": payload.razorpay_order_id,
            "provider": "razorpay",
            "status": "paid",
            "order_state": payment.order_state,
            "payment_state": payment.payment_state,
            "provider_order_id": payment.provider_order_id,
            "provider_payment_id": payment.provider_payment_id,
            "provider_signature": payment.provider_signature,
            "attempt_count": payment.attempt_count,
            "order_ids": order_ids,
            "verified_at": payment.verified_at,
            "updated_at": payment.updated_at,
            "source": "payment-verify",
        },
        upsert_filter={"payment_reference": payment.payment_reference},
    )
    if payment_was_already_paid:
        return schemas.MessageResponse(message="Payment already verified")
    return schemas.MessageResponse(message="Payment verified successfully")


@router.post("/payments/failure", response_model=schemas.MessageResponse)
def report_payment_failure(
    payload: schemas.RazorpayFailureRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles(models.UserRole.STUDENT)),
):
    payment = (
        db.query(models.FoodPayment)
        .filter(
            (models.FoodPayment.provider_order_id == payload.razorpay_order_id)
            | (models.FoodPayment.payment_reference == payload.razorpay_order_id)
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment reference not found")
    if not current_user.student_id or payment.student_id != current_user.student_id:
        raise HTTPException(status_code=403, detail="Cannot update payment for another student")
    if _is_payment_paid(payment):
        return schemas.MessageResponse(message="Payment already captured")

    gateway_status, gateway_payment_id = _fetch_razorpay_gateway_status(
        provider_order_id=payload.razorpay_order_id,
        provider_payment_id=payload.razorpay_payment_id,
    )
    if gateway_status == "paid":
        resolved_payment_id = (
            str(gateway_payment_id or "").strip()
            or str(payload.razorpay_payment_id or "").strip()
            or str(payment.provider_payment_id or "").strip()
            or str(payload.razorpay_order_id or "").strip()
        )
        payment.provider = "razorpay"
        payment.provider_order_id = payload.razorpay_order_id
        payment.provider_payment_id = resolved_payment_id
        payment.attempt_count = int(payment.attempt_count or 0) + 1
        payment.order_state = "paid"
        payment.payment_state = "captured"
        payment.status = "paid"
        payment.failed_reason = None
        payment.updated_at = datetime.utcnow()
        payment.verified_at = payment.verified_at or datetime.utcnow()
        payment.webhook_payload_json = json.dumps(
            {
                "reconciled_from": "failure_callback",
                "razorpay_order_id": payload.razorpay_order_id,
                "razorpay_payment_id": resolved_payment_id,
            }
        )

        order_ids = json.loads(payment.order_ids_json or "[]")
        if not isinstance(order_ids, list):
            order_ids = []
        orders = db.query(models.FoodOrder).filter(models.FoodOrder.id.in_(order_ids)).all()
        orders_changed: list[tuple[models.FoodOrder, models.FoodOrderStatus, str, str, bool]] = []
        for order in orders:
            previous_status = order.status
            previous_payment_status = str(order.payment_status or "")
            previous_payment_ref = str(order.payment_reference or "")
            transitioned = False

            order.payment_status = "paid"
            order.payment_provider = "razorpay"
            order.payment_reference = resolved_payment_id
            if order.status == models.FoodOrderStatus.PLACED:
                _apply_status_transition(order, models.FoodOrderStatus.VERIFIED, note="Payment verified via Razorpay")
                transitioned = True
            order_mutated = (
                previous_status != order.status
                or previous_payment_status != str(order.payment_status or "")
                or previous_payment_ref != str(order.payment_reference or "")
            )
            if not order_mutated:
                continue
            orders_changed.append((order, previous_status, previous_payment_status, previous_payment_ref, transitioned))

        for order, previous_status, previous_payment_status, previous_payment_ref, transitioned in orders_changed:
            if transitioned:
                _notify_order_status(db, order, "Order verified.")
            _record_order_audit(
                db,
                order,
                event_type="payment_failure_reconciled",
                actor=current_user,
                from_status=previous_status.value,
                to_status=order.status.value,
                message="Payment reconciled as captured from Razorpay gateway",
                payload={
                    "provider": "razorpay",
                    "provider_order_id": payload.razorpay_order_id,
                    "provider_payment_id": resolved_payment_id,
                    "previous_payment_status": previous_payment_status,
                    "previous_payment_reference": previous_payment_ref,
                    "reconciled_from": "payment_failed_callback",
                },
            )

        db.commit()
        for order, _, _, _, _ in orders_changed:
            _sync_order_document(order, "payment-failure-reconciled")
        _try_clear_food_cart(student_id=int(payment.student_id), user_id=current_user.id)
        mirror_document(
            "food_payments",
            {
                "payment_reference": payment.payment_reference,
                "provider": "razorpay",
                "status": payment.status,
                "order_state": payment.order_state,
                "payment_state": payment.payment_state,
                "provider_order_id": payment.provider_order_id,
                "provider_payment_id": payment.provider_payment_id,
                "attempt_count": payment.attempt_count,
                "order_ids": order_ids,
                "verified_at": payment.verified_at,
                "updated_at": payment.updated_at,
                "source": "payment-failure-reconciled",
            },
            upsert_filter={"payment_reference": payment.payment_reference},
        )
        return schemas.MessageResponse(message="Payment already captured on Razorpay; reconciled successfully")

    reason_bits = [
        payload.error_description,
        payload.error_reason,
        payload.error_code,
    ]
    failed_reason = " | ".join([str(bit).strip() for bit in reason_bits if str(bit or "").strip()]) or "payment_failed"
    existing_provider_order_id = str(payment.provider_order_id or "").strip()
    existing_provider_payment_id = str(payment.provider_payment_id or "").strip()
    incoming_provider_order_id = str(payload.razorpay_order_id or "").strip()
    incoming_provider_payment_id = str(payload.razorpay_payment_id or "").strip()
    if (
        str(payment.status or "").strip().lower() == "failed"
        and existing_provider_order_id == incoming_provider_order_id
        and (
            not incoming_provider_payment_id
            or not existing_provider_payment_id
            or incoming_provider_payment_id == existing_provider_payment_id
        )
        and str(payment.failed_reason or "").strip() == failed_reason
    ):
        return schemas.MessageResponse(message="Payment failure already recorded")

    payment.provider = "razorpay"
    payment.provider_order_id = payload.razorpay_order_id
    payment.provider_payment_id = payload.razorpay_payment_id
    payment.attempt_count = int(payment.attempt_count or 0) + 1
    payment.order_state = "attempted"
    payment.payment_state = "failed"
    payment.status = "failed"
    payment.updated_at = datetime.utcnow()
    payment.failed_reason = failed_reason
    payment.webhook_payload_json = json.dumps(
        {
            "error_code": payload.error_code,
            "error_description": payload.error_description,
            "error_source": payload.error_source,
            "error_step": payload.error_step,
            "error_reason": payload.error_reason,
            "razorpay_payment_id": payload.razorpay_payment_id,
            "razorpay_order_id": payload.razorpay_order_id,
        }
    )

    order_ids = json.loads(payment.order_ids_json or "[]")
    if not isinstance(order_ids, list):
        order_ids = []
    orders = db.query(models.FoodOrder).filter(models.FoodOrder.id.in_(order_ids)).all()
    orders_changed: list[tuple[models.FoodOrder, models.FoodOrderStatus, str, str]] = []
    for order in orders:
        previous_status = order.status
        previous_payment_status = str(order.payment_status or "")
        previous_payment_ref = str(order.payment_reference or "")
        order.payment_status = "failed"
        order.payment_provider = "razorpay"
        order.payment_reference = payload.razorpay_order_id
        order_mutated = (
            previous_status != order.status
            or previous_payment_status != str(order.payment_status or "")
            or previous_payment_ref != str(order.payment_reference or "")
        )
        if not order_mutated:
            continue
        orders_changed.append((order, previous_status, previous_payment_status, previous_payment_ref))

    for order, previous_status, previous_payment_status, previous_payment_ref in orders_changed:
        _notify_order_status(db, order, "Payment failed. Please retry checkout.")
        _record_order_audit(
            db,
            order,
            event_type="payment_failed_client",
            actor=current_user,
            from_status=previous_status.value,
            to_status=order.status.value,
            message="Payment failed on client",
            payload={
                "provider": "razorpay",
                "provider_order_id": payload.razorpay_order_id,
                "provider_payment_id": payload.razorpay_payment_id,
                "error_code": payload.error_code,
                "error_description": payload.error_description,
                "error_source": payload.error_source,
                "error_step": payload.error_step,
                "error_reason": payload.error_reason,
                "previous_payment_status": previous_payment_status,
                "previous_payment_reference": previous_payment_ref,
            },
        )

    db.commit()
    for order, _, _, _ in orders_changed:
        _sync_order_document(order, "payment-failure")
    mirror_document(
        "food_payments",
        {
            "payment_reference": payment.payment_reference,
            "provider": "razorpay",
            "status": payment.status,
            "order_state": payment.order_state,
            "payment_state": payment.payment_state,
            "provider_order_id": payment.provider_order_id,
            "provider_payment_id": payment.provider_payment_id,
            "attempt_count": payment.attempt_count,
            "failed_reason": payment.failed_reason,
            "order_ids": order_ids,
            "updated_at": payment.updated_at,
            "source": "payment-failure",
        },
        upsert_filter={"payment_reference": payment.payment_reference},
    )
    return schemas.MessageResponse(message="Payment failure recorded")
