#!/usr/bin/env python3
"""
Quick end-to-end smoke script for:
checkout -> payment failure -> recovery -> rating

It uses existing authenticated users and live API endpoints.
Provide a student auth token via --token (or AUTH_TOKEN env).
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import date
from urllib import error, request


FINAL_STATUSES = {"delivered", "cancelled", "rejected", "refunded", "collected"}


def _decode_json(raw: bytes):
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def api_call(
    *,
    base_url: str,
    method: str,
    path: str,
    token: str,
    body=None,
    raw_body: bytes | None = None,
    extra_headers: dict | None = None,
    expected_statuses=(200, 201),
    timeout_sec: int = 20,
):
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if raw_body is not None:
        payload = raw_body
        headers["Content-Type"] = "application/json"
    elif body is None:
        payload = None
    else:
        payload = json.dumps(body, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)

    req = request.Request(url=url, data=payload, method=method.upper(), headers=headers)
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read()
            status_code = int(resp.status)
    except error.HTTPError as exc:
        raw = exc.read()
        detail = _decode_json(raw)
        raise RuntimeError(f"{method.upper()} {path} failed ({exc.code}): {detail}") from exc

    parsed = _decode_json(raw)
    if status_code not in expected_statuses:
        raise RuntimeError(f"{method.upper()} {path} unexpected status {status_code}: {parsed}")
    return parsed


def choose_menu_item(menu_items: list[dict]) -> dict:
    for row in menu_items:
        if not row.get("is_active", True):
            continue
        if row.get("sold_out", False):
            continue
        stock = row.get("stock_quantity")
        if stock is not None and int(stock) <= 0:
            continue
        return row
    raise RuntimeError("No active in-stock menu item found")


def find_delivered_order(orders: list[dict]) -> dict | None:
    for row in orders:
        if str(row.get("status") or "").strip().lower() == "delivered":
            return row
    return None


def print_step(text: str):
    print(f"\n[step] {text}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Food payment hardening e2e smoke test")
    parser.add_argument("--base-url", default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--token", default=os.getenv("AUTH_TOKEN", ""))
    parser.add_argument("--operator-token", default=os.getenv("OPERATOR_TOKEN", ""))
    parser.add_argument("--webhook-token", default=os.getenv("FOOD_PAYMENT_WEBHOOK_TOKEN", ""))
    parser.add_argument("--signed-webhook-secret", default=os.getenv("RAZORPAY_WEBHOOK_SECRET", ""))
    parser.add_argument("--order-date", default=os.getenv("ORDER_DATE", date.today().isoformat()))
    parser.add_argument("--lpu-lat", type=float, default=float(os.getenv("LPU_CENTER_LAT", "31.2536")))
    parser.add_argument("--lpu-lon", type=float, default=float(os.getenv("LPU_CENTER_LON", "75.7064")))
    parser.add_argument("--accuracy-m", type=float, default=float(os.getenv("LPU_GPS_ACCURACY_M", "25")))
    parser.add_argument("--rating", type=int, default=int(os.getenv("ORDER_RATING_STARS", "5")))
    args = parser.parse_args()

    if not args.token:
        print("AUTH token is required. Pass --token or set AUTH_TOKEN.", file=sys.stderr)
        return 2
    rating_stars = max(1, min(5, int(args.rating)))

    print_step("Validate current user")
    me = api_call(base_url=args.base_url, method="GET", path="/auth/me", token=args.token, expected_statuses=(200,))
    if str(me.get("role")) != "student":
        raise RuntimeError(f"Script requires student token; got role={me.get('role')}")
    student_id = int(me.get("student_id") or 0)
    if not student_id:
        raise RuntimeError("Token user is missing student_id")
    print(f"[info] student_id={student_id}, email={me.get('email')}")

    print_step("Load shop/menu/slot metadata")
    shops = api_call(
        base_url=args.base_url,
        method="GET",
        path="/food/shops?active_only=true",
        token=args.token,
        expected_statuses=(200,),
    )
    if not isinstance(shops, list) or not shops:
        raise RuntimeError("No active shops available")
    shop = shops[0]
    shop_id = int(shop["id"])
    menu_items = api_call(
        base_url=args.base_url,
        method="GET",
        path=f"/food/shops/{shop_id}/menu-items",
        token=args.token,
        expected_statuses=(200,),
    )
    if not isinstance(menu_items, list) or not menu_items:
        raise RuntimeError(f"No menu items found for shop_id={shop_id}")
    menu_item = choose_menu_item(menu_items)
    slots = api_call(
        base_url=args.base_url,
        method="GET",
        path="/food/slots",
        token=args.token,
        expected_statuses=(200,),
    )
    if not isinstance(slots, list) or not slots:
        raise RuntimeError("No slots found")
    slot_id = int(slots[0]["id"])
    print(f"[info] shop_id={shop_id}, menu_item_id={menu_item['id']}, slot_id={slot_id}, order_date={args.order_date}")

    print_step("Create checkout order")
    checkout_key = f"e2e-{uuid.uuid4().hex[:16]}"
    checkout_payload = {
        "student_id": student_id,
        "shop_id": shop_id,
        "slot_id": slot_id,
        "order_date": args.order_date,
        "idempotency_key": checkout_key,
        "shop_name": shop.get("name"),
        "shop_block": shop.get("block"),
        "pickup_point": "E2E Delivery Point",
        "location_latitude": args.lpu_lat,
        "location_longitude": args.lpu_lon,
        "location_accuracy_m": args.accuracy_m,
        "items": [
            {
                "menu_item_id": int(menu_item["id"]),
                "food_item_id": int(menu_item.get("food_item_id") or 0) or None,
                "quantity": 1,
                "status_note": "e2e-checkout",
            }
        ],
    }
    created_orders = api_call(
        base_url=args.base_url,
        method="POST",
        path="/food/orders/checkout",
        token=args.token,
        body=checkout_payload,
        extra_headers={"X-Idempotency-Key": checkout_key},
        expected_statuses=(201,),
    )
    if not isinstance(created_orders, list) or not created_orders:
        raise RuntimeError("Checkout did not return created orders")
    order_ids = [int(row["id"]) for row in created_orders]
    print(f"[info] created_order_ids={order_ids}")

    print_step("Create payment intent and mark failure")
    failed_intent = api_call(
        base_url=args.base_url,
        method="POST",
        path="/food/payments/intent",
        token=args.token,
        body={"order_ids": order_ids, "provider": "sandbox"},
        expected_statuses=(200,),
    )
    failed_ref = str(failed_intent.get("provider_order_id") or failed_intent.get("payment_reference") or "").strip()
    if not failed_ref:
        raise RuntimeError("Payment intent missing payment reference")
    failure_response = api_call(
        base_url=args.base_url,
        method="POST",
        path="/food/payments/failure",
        token=args.token,
        body={
            "razorpay_order_id": failed_ref,
            "razorpay_payment_id": f"sim_fail_{uuid.uuid4().hex[:8]}",
            "error_code": "E2E_FAIL",
            "error_description": "Simulated failure",
            "error_source": "e2e-script",
            "error_step": "payment_submit",
            "error_reason": "simulated_failure",
        },
        expected_statuses=(200,),
    )
    print(f"[info] failure_callback={failure_response}")

    print_step("Verify recovery candidates include failed payment")
    recovery_rows = api_call(
        base_url=args.base_url,
        method="GET",
        path="/food/payments/recovery",
        token=args.token,
        expected_statuses=(200,),
    )
    if not isinstance(recovery_rows, list):
        raise RuntimeError("Recovery API did not return a list")
    failed_recovery = next(
        (row for row in recovery_rows if str(row.get("payment_reference")) == str(failed_intent.get("payment_reference"))),
        None,
    )
    if not failed_recovery:
        raise RuntimeError("Failed payment was not returned in /food/payments/recovery")
    print(f"[info] recovery_candidate_found={failed_recovery.get('payment_reference')}")

    print_step("Recovery retry: new payment intent + paid webhook")
    recovery_intent = api_call(
        base_url=args.base_url,
        method="POST",
        path="/food/payments/intent",
        token=args.token,
        body={"order_ids": order_ids, "provider": "sandbox"},
        expected_statuses=(200,),
    )
    recovery_ref = str(recovery_intent.get("payment_reference") or "").strip()
    webhook_headers = {}
    if args.webhook_token:
        webhook_headers["X-Webhook-Token"] = args.webhook_token
    paid_payload = {
        "payment_reference": recovery_ref,
        "status": "paid",
        "provider": "sandbox",
        "payload": {
            "payment_id": f"sim_paid_{uuid.uuid4().hex[:8]}",
            "event": "e2e.recovery.paid",
        },
    }
    webhook_processed = api_call(
        base_url=args.base_url,
        method="POST",
        path="/food/payments/webhook",
        token=args.token,
        body=paid_payload,
        extra_headers=webhook_headers,
        expected_statuses=(200,),
    )
    print(f"[info] webhook_processed={webhook_processed}")

    replay_response = api_call(
        base_url=args.base_url,
        method="POST",
        path="/food/payments/webhook",
        token=args.token,
        body=paid_payload,
        extra_headers=webhook_headers,
        expected_statuses=(200,),
    )
    replay_message = str(replay_response.get("message") or "")
    if "already processed" not in replay_message.lower():
        raise RuntimeError(f"Replay protection check failed: {replay_response}")
    print(f"[info] replay_protection={replay_response}")

    if args.signed_webhook_secret:
        print_step("Signed Razorpay webhook path + replay check")
        signed_intent = api_call(
            base_url=args.base_url,
            method="POST",
            path="/food/payments/intent",
            token=args.token,
            body={"order_ids": order_ids, "provider": "sandbox"},
            expected_statuses=(200,),
        )
        signed_payload = {
            "payment_reference": str(signed_intent.get("payment_reference") or ""),
            "status": "paid",
            "provider": "razorpay",
            "payload": {
                "payment_id": f"sim_rzp_{uuid.uuid4().hex[:8]}",
                "event": "e2e.signed.paid",
            },
        }
        signed_raw = json.dumps(signed_payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        signed_sig = hmac.new(
            args.signed_webhook_secret.encode("utf-8"),
            signed_raw,
            hashlib.sha256,
        ).hexdigest()
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        signed_headers = {"X-Razorpay-Signature": signed_sig, "X-Razorpay-Event-Id": event_id}
        if args.webhook_token:
            signed_headers["X-Webhook-Token"] = args.webhook_token
        signed_first = api_call(
            base_url=args.base_url,
            method="POST",
            path="/food/payments/webhook",
            token=args.token,
            raw_body=signed_raw,
            extra_headers=signed_headers,
            expected_statuses=(200,),
        )
        signed_replay = api_call(
            base_url=args.base_url,
            method="POST",
            path="/food/payments/webhook",
            token=args.token,
            raw_body=signed_raw,
            extra_headers=signed_headers,
            expected_statuses=(200,),
        )
        print(f"[info] signed_webhook_first={signed_first}")
        print(f"[info] signed_webhook_replay={signed_replay}")

    print_step("Find delivered order (or promote one if operator token provided)")
    orders_after_recovery = api_call(
        base_url=args.base_url,
        method="GET",
        path="/food/orders?limit=200",
        token=args.token,
        expected_statuses=(200,),
    )
    delivered = find_delivered_order(orders_after_recovery if isinstance(orders_after_recovery, list) else [])
    if not delivered and args.operator_token:
        promote_id = order_ids[0]
        for status_value in ["preparing", "out_for_delivery", "delivered"]:
            api_call(
                base_url=args.base_url,
                method="PATCH",
                path=f"/food/orders/{promote_id}/status",
                token=args.operator_token,
                body={"status": status_value, "status_note": "e2e promote to delivered"},
                expected_statuses=(200,),
            )
        orders_after_recovery = api_call(
            base_url=args.base_url,
            method="GET",
            path="/food/orders?limit=200",
            token=args.token,
            expected_statuses=(200,),
        )
        delivered = next(
            (row for row in orders_after_recovery if int(row.get("id") or 0) == promote_id and str(row.get("status")) == "delivered"),
            None,
        )

    if delivered:
        delivered_id = int(delivered["id"])
        print(f"[info] rating_order_id={delivered_id}")
        rated = api_call(
            base_url=args.base_url,
            method="PATCH",
            path=f"/food/orders/{delivered_id}/rating",
            token=args.token,
            body={"stars": rating_stars},
            expected_statuses=(200,),
        )
        if int(rated.get("rating_stars") or 0) != rating_stars:
            raise RuntimeError(f"Rating set mismatch: {rated}")
        unrated = api_call(
            base_url=args.base_url,
            method="PATCH",
            path=f"/food/orders/{delivered_id}/rating",
            token=args.token,
            body={"stars": 0},
            expected_statuses=(200,),
        )
        if unrated.get("rating_stars") is not None:
            raise RuntimeError(f"Rating unset mismatch: {unrated}")
        print(f"[info] rating_set_and_unset_ok_for_order={delivered_id}")
    else:
        print("[warn] No delivered order available for rating. Provide --operator-token to force status transitions.")

    print_step("Summary")
    history = api_call(
        base_url=args.base_url,
        method="GET",
        path="/food/orders?limit=200",
        token=args.token,
        expected_statuses=(200,),
    )
    rows = history if isinstance(history, list) else []
    current_count = sum(1 for row in rows if str(row.get("status") or "").strip().lower() not in FINAL_STATUSES)
    previous_count = len(rows) - current_count
    print(f"[done] total_orders={len(rows)} current={current_count} previous={previous_count}")
    print("[done] checkout -> failure -> recovery -> rating flow completed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - script failure path
        print(f"[error] {exc}", file=sys.stderr)
        raise
