import hashlib
import hmac
import unittest
from unittest.mock import patch

from pymongo.errors import DuplicateKeyError

from app.routers.food import (
    _fetch_razorpay_gateway_status,
    _extract_razorpay_webhook_fields,
    _normalize_razorpay_gateway_status,
    _register_payment_webhook_event,
    _verify_razorpay_webhook_signature,
)


class _FakeWebhookEventsCollection:
    def __init__(self):
        self._event_keys = set()
        self._fingerprint_keys = set()

    def insert_one(self, body):
        provider = str(body.get("provider") or "").strip().lower()
        event_id = str(body.get("event_id") or "").strip()
        fingerprint = str(body.get("fingerprint") or "").strip()

        if event_id:
            event_key = (provider, event_id)
            if event_key in self._event_keys:
                raise DuplicateKeyError("duplicate provider/event_id")
        fingerprint_key = (provider, fingerprint)
        if fingerprint_key in self._fingerprint_keys:
            raise DuplicateKeyError("duplicate provider/fingerprint")

        if event_id:
            self._event_keys.add((provider, event_id))
        self._fingerprint_keys.add(fingerprint_key)
        return {"ok": 1}


class _FakeMongoDB:
    def __init__(self):
        self._collections = {"payment_webhook_events": _FakeWebhookEventsCollection()}

    def __getitem__(self, name):
        return self._collections[name]


class _FakeRazorpayPaymentClient:
    def __init__(self, fetch_result=None, fetch_error=None):
        self._fetch_result = fetch_result
        self._fetch_error = fetch_error

    def fetch(self, _payment_id):
        if self._fetch_error is not None:
            raise self._fetch_error
        return self._fetch_result


class _FakeRazorpayOrderClient:
    def __init__(self, payments_result=None, payments_error=None):
        self._payments_result = payments_result
        self._payments_error = payments_error

    def payments(self, _order_id):
        if self._payments_error is not None:
            raise self._payments_error
        return self._payments_result


class _FakeRazorpayClient:
    def __init__(self, fetch_result=None, fetch_error=None, payments_result=None, payments_error=None):
        self.payment = _FakeRazorpayPaymentClient(fetch_result=fetch_result, fetch_error=fetch_error)
        self.order = _FakeRazorpayOrderClient(payments_result=payments_result, payments_error=payments_error)


class FoodPaymentHardeningTests(unittest.TestCase):
    def test_normalize_razorpay_gateway_status(self):
        self.assertEqual(_normalize_razorpay_gateway_status("captured"), "paid")
        self.assertEqual(_normalize_razorpay_gateway_status("PAID"), "paid")
        self.assertEqual(_normalize_razorpay_gateway_status("authorized"), "attempted")
        self.assertEqual(_normalize_razorpay_gateway_status("created"), "attempted")
        self.assertEqual(_normalize_razorpay_gateway_status("failed"), "failed")
        self.assertIsNone(_normalize_razorpay_gateway_status(""))
        self.assertIsNone(_normalize_razorpay_gateway_status(None))

    def test_verify_razorpay_webhook_signature(self):
        secret = "whsec_test_secret"
        raw_body = b'{"event":"payment.captured","payload":{"x":1}}'
        signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        self.assertTrue(
            _verify_razorpay_webhook_signature(
                secret=secret,
                raw_body=raw_body,
                incoming_signature=signature,
            )
        )
        self.assertFalse(
            _verify_razorpay_webhook_signature(
                secret=secret,
                raw_body=b'{"event":"payment.captured","payload":{"x":2}}',
                incoming_signature=signature,
            )
        )
        self.assertFalse(
            _verify_razorpay_webhook_signature(
                secret=secret,
                raw_body=raw_body,
                incoming_signature="bad-signature",
            )
        )

    def test_extract_razorpay_webhook_fields_order_paid(self):
        raw_payload = {
            "event": "order.paid",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_abc123",
                        "order_id": "order_xyz987",
                        "status": "captured",
                    }
                },
                "order": {"entity": {"id": "order_xyz987"}},
            },
        }

        provider_order_id, provider_payment_id, normalized_status, normalized_payload = _extract_razorpay_webhook_fields(
            raw_payload
        )

        self.assertEqual(provider_order_id, "order_xyz987")
        self.assertEqual(provider_payment_id, "pay_abc123")
        self.assertEqual(normalized_status, "paid")
        self.assertEqual(normalized_payload.get("event"), "order.paid")
        self.assertEqual(normalized_payload.get("payment_status"), "captured")

    def test_register_payment_webhook_event_replay_by_event_id(self):
        mongo_db = _FakeMongoDB()

        first = _register_payment_webhook_event(
            mongo_db=mongo_db,
            provider="razorpay",
            event_id="evt_001",
            fingerprint="fp_001",
            signature="sig_1",
            payload={"a": 1},
        )
        second = _register_payment_webhook_event(
            mongo_db=mongo_db,
            provider="razorpay",
            event_id="evt_001",
            fingerprint="fp_002",
            signature="sig_2",
            payload={"a": 2},
        )

        self.assertFalse(first)
        self.assertTrue(second)

    def test_register_payment_webhook_event_replay_by_fingerprint(self):
        mongo_db = _FakeMongoDB()

        first = _register_payment_webhook_event(
            mongo_db=mongo_db,
            provider="razorpay",
            event_id="evt_100",
            fingerprint="same_fp",
            signature="sig_100",
            payload={"a": 100},
        )
        second = _register_payment_webhook_event(
            mongo_db=mongo_db,
            provider="razorpay",
            event_id="evt_101",
            fingerprint="same_fp",
            signature="sig_101",
            payload={"a": 101},
        )

        self.assertFalse(first)
        self.assertTrue(second)

    def test_fetch_gateway_status_prefers_payment_fetch_paid(self):
        fake_client = _FakeRazorpayClient(
            fetch_result={"id": "pay_live_1", "order_id": "order_live_1", "status": "captured"},
            payments_result={"items": [{"id": "pay_old", "status": "failed"}]},
        )
        with patch("app.routers.food._get_razorpay_client", return_value=fake_client):
            status, payment_id = _fetch_razorpay_gateway_status(
                provider_order_id=None,
                provider_payment_id="pay_live_1",
            )

        self.assertEqual(status, "paid")
        self.assertEqual(payment_id, "pay_live_1")

    def test_fetch_gateway_status_uses_order_payments_best_rank(self):
        fake_client = _FakeRazorpayClient(
            fetch_error=RuntimeError("fetch unavailable"),
            payments_result={
                "items": [
                    {"id": "pay_failed", "status": "failed"},
                    {"id": "pay_auth", "status": "authorized"},
                    {"id": "pay_captured", "status": "captured"},
                ]
            },
        )
        with patch("app.routers.food._get_razorpay_client", return_value=fake_client):
            status, payment_id = _fetch_razorpay_gateway_status(
                provider_order_id="order_live_2",
                provider_payment_id=None,
            )

        self.assertEqual(status, "paid")
        self.assertEqual(payment_id, "pay_captured")


if __name__ == "__main__":
    unittest.main()
