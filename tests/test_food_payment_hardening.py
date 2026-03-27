import hashlib
import hmac
import unittest
from datetime import date, time
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.auth_utils import CurrentUser
from pymongo.errors import DuplicateKeyError

from app.routers.food import (
    _fetch_razorpay_gateway_status,
    _notify_order_status,
    _order_counts_towards_food_hall_totals,
    _mirror_food_payment,
    _prepare_food_checkout_transaction,
    _razorpay_webhook_secrets,
    _extract_razorpay_webhook_fields,
    _normalize_razorpay_gateway_status,
    _resolve_razorpay_keyring,
    _register_payment_webhook_event,
    _verify_razorpay_webhook_signature,
    food_ops_metrics,
    get_slot_demand,
    report_payment_failure,
    verify_payment,
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
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    @staticmethod
    def _student_user(*, user_id: int = 51, student_id: int = 7) -> CurrentUser:
        return CurrentUser(
            id=user_id,
            email=f"student{user_id}@example.com",
            role=models.UserRole.STUDENT,
            student_id=student_id,
            faculty_id=None,
            alternate_email=None,
            primary_login_verified=True,
            is_active=True,
        )

    @staticmethod
    def _admin_user(*, user_id: int = 1) -> CurrentUser:
        return CurrentUser(
            id=user_id,
            email=f"admin{user_id}@example.com",
            role=models.UserRole.ADMIN,
            student_id=None,
            faculty_id=None,
            alternate_email=None,
            primary_login_verified=True,
            is_active=True,
        )

    def test_normalize_razorpay_gateway_status(self):
        self.assertEqual(_normalize_razorpay_gateway_status("captured"), "paid")
        self.assertEqual(_normalize_razorpay_gateway_status("PAID"), "paid")
        self.assertEqual(_normalize_razorpay_gateway_status("authorized"), "attempted")
        self.assertEqual(_normalize_razorpay_gateway_status("created"), "attempted")
        self.assertEqual(_normalize_razorpay_gateway_status("failed"), "failed")
        self.assertIsNone(_normalize_razorpay_gateway_status(""))
        self.assertIsNone(_normalize_razorpay_gateway_status(None))

    def test_order_counts_towards_food_hall_totals_excludes_unpaid_placed_rows(self):
        self.assertFalse(
            _order_counts_towards_food_hall_totals(
                status_value=models.FoodOrderStatus.PLACED,
                payment_status="pending",
            )
        )
        self.assertTrue(
            _order_counts_towards_food_hall_totals(
                status_value=models.FoodOrderStatus.PLACED,
                payment_status="paid",
            )
        )
        self.assertTrue(
            _order_counts_towards_food_hall_totals(
                status_value=models.FoodOrderStatus.VERIFIED,
                payment_status="created",
            )
        )
        self.assertFalse(
            _order_counts_towards_food_hall_totals(
                status_value=models.FoodOrderStatus.REFUND_PENDING,
                payment_status="paid",
            )
        )

    def test_get_slot_demand_excludes_unpaid_placed_rows(self):
        self.db.add_all(
            [
                models.Student(
                    id=7,
                    name="Student Seven",
                    email="student7@example.com",
                    department="CSE",
                    semester=6,
                ),
                models.FoodItem(id=1, name="Wrap", price=120.0, is_active=True),
                models.BreakSlot(
                    id=1,
                    label="10:00 - 11:00",
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    max_orders=50,
                ),
            ]
        )
        self.db.flush()
        self.db.add_all(
            [
                models.FoodOrder(
                    id=201,
                    student_id=7,
                    food_item_id=1,
                    slot_id=1,
                    order_date=date(2026, 3, 24),
                    quantity=1,
                    unit_price=120.0,
                    total_price=120.0,
                    status=models.FoodOrderStatus.PLACED,
                    payment_status="pending",
                ),
                models.FoodOrder(
                    id=202,
                    student_id=7,
                    food_item_id=1,
                    slot_id=1,
                    order_date=date(2026, 3, 24),
                    quantity=1,
                    unit_price=120.0,
                    total_price=120.0,
                    status=models.FoodOrderStatus.PLACED,
                    payment_status="paid",
                ),
                models.FoodOrder(
                    id=203,
                    student_id=7,
                    food_item_id=1,
                    slot_id=1,
                    order_date=date(2026, 3, 24),
                    quantity=1,
                    unit_price=120.0,
                    total_price=120.0,
                    status=models.FoodOrderStatus.CANCELLED,
                    payment_status="paid",
                ),
            ]
        )
        self.db.commit()

        with patch("app.routers.food._slot_demand_from_mongo", return_value=None):
            rows = get_slot_demand(
                order_date=date(2026, 3, 24),
                db=self.db,
                _=self._student_user(),
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].orders, 1)

    def test_food_ops_metrics_active_orders_ignore_unpaid_placed_rows(self):
        self.db.add_all(
            [
                models.Student(
                    id=7,
                    name="Student Seven",
                    email="student7@example.com",
                    department="CSE",
                    semester=6,
                ),
                models.FoodItem(id=1, name="Wrap", price=120.0, is_active=True),
                models.BreakSlot(
                    id=1,
                    label="10:00 - 11:00",
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    max_orders=50,
                ),
            ]
        )
        self.db.flush()
        self.db.add_all(
            [
                models.FoodOrder(
                    id=301,
                    student_id=7,
                    food_item_id=1,
                    slot_id=1,
                    order_date=date.today(),
                    quantity=1,
                    unit_price=120.0,
                    total_price=120.0,
                    status=models.FoodOrderStatus.PLACED,
                    payment_status="pending",
                ),
                models.FoodOrder(
                    id=302,
                    student_id=7,
                    food_item_id=1,
                    slot_id=1,
                    order_date=date.today(),
                    quantity=1,
                    unit_price=120.0,
                    total_price=120.0,
                    status=models.FoodOrderStatus.PLACED,
                    payment_status="paid",
                ),
                models.FoodOrder(
                    id=303,
                    student_id=7,
                    food_item_id=1,
                    slot_id=1,
                    order_date=date.today(),
                    quantity=1,
                    unit_price=120.0,
                    total_price=120.0,
                    status=models.FoodOrderStatus.DELIVERED,
                    payment_status="paid",
                ),
            ]
        )
        self.db.commit()

        metrics = food_ops_metrics(db=self.db, current_user=self._admin_user())

        self.assertEqual(metrics.active_orders, 1)

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

    def test_resolve_razorpay_keyring_prefers_active_entry(self):
        payload = {
            "RAZORPAY_KEYRING_JSON": '{"v1":{"key_id":"rzp_old","key_secret":"sec_old"},"v2":{"key_id":"rzp_new","key_secret":"sec_new"}}',
            "RAZORPAY_ACTIVE_KEY_ID": "v2",
            "RAZORPAY_KEY_ID": "rzp_fallback",
            "RAZORPAY_KEY_SECRET": "sec_fallback",
        }

        def _fake_resolve(name, default=""):
            return payload.get(name, default)

        with patch("app.routers.food.resolve_secret", side_effect=_fake_resolve):
            keyring = _resolve_razorpay_keyring()

        self.assertEqual(keyring[0], ("rzp_new", "sec_new"))
        self.assertIn(("rzp_old", "sec_old"), keyring)
        self.assertIn(("rzp_fallback", "sec_fallback"), keyring)

    def test_razorpay_webhook_secrets_prioritize_active_secret(self):
        payload = {
            "RAZORPAY_WEBHOOK_SECRETS_JSON": '{"v1":"secret_old","v2":"secret_new"}',
            "RAZORPAY_WEBHOOK_ACTIVE_SECRET_ID": "v2",
            "RAZORPAY_WEBHOOK_SECRET": "secret_legacy",
        }

        def _fake_resolve(name, default=""):
            return payload.get(name, default)

        with patch("app.routers.food.resolve_secret", side_effect=_fake_resolve):
            secrets = _razorpay_webhook_secrets()

        self.assertEqual(secrets[0], "secret_new")
        self.assertIn("secret_old", secrets)
        self.assertIn("secret_legacy", secrets)

    def test_verify_payment_mirrors_canonical_payment_reference(self):
        self.db.add_all(
            [
                models.Student(
                    id=7,
                    name="Student Seven",
                    email="student7@example.com",
                    department="CSE",
                    semester=6,
                ),
                models.FoodItem(id=1, name="Wrap", price=120.0, is_active=True),
                models.BreakSlot(
                    id=1,
                    label="10:00 - 11:00",
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    max_orders=50,
                ),
            ]
        )
        self.db.flush()

        order = models.FoodOrder(
            id=101,
            student_id=7,
            food_item_id=1,
            slot_id=1,
            order_date=date(2026, 3, 24),
            quantity=1,
            unit_price=120.0,
            total_price=120.0,
            status=models.FoodOrderStatus.PLACED,
            payment_status="pending",
            payment_reference=None,
        )
        payment = models.FoodPayment(
            student_id=7,
            amount=120.0,
            provider="razorpay",
            payment_reference="PAY-LOCAL-1001",
            provider_order_id="order_rzp_1001",
            status="created",
            order_state="created",
            payment_state="created",
            order_ids_json="[101]",
        )
        self.db.add_all([order, payment])
        self.db.commit()

        payload = schemas.RazorpayVerifyRequest(
            razorpay_payment_id="pay_rzp_1001",
            razorpay_order_id="order_rzp_1001",
            razorpay_signature="sig_1001",
        )
        current_user = self._student_user()
        mirrored_calls: list[dict] = []

        class _FakeRazorpayUtility:
            @staticmethod
            def verify_payment_signature(_payload):
                return True

        class _FakeRazorpayClient:
            utility = _FakeRazorpayUtility()

        def _capture_mirror(collection_name, payload, **kwargs):
            mirrored_calls.append(
                {
                    "collection_name": collection_name,
                    "payload": payload,
                    "kwargs": kwargs,
                }
            )

        with (
            patch("app.routers.food._get_razorpay_client", return_value=_FakeRazorpayClient()),
            patch("app.routers.food.mirror_document", side_effect=_capture_mirror),
            patch("app.routers.food._sync_order_document", return_value=None),
            patch("app.routers.food._try_clear_food_cart", return_value=None),
        ):
            response = verify_payment(payload=payload, db=self.db, current_user=current_user)

        self.assertEqual(response.message, "Payment verified successfully")
        self.assertTrue(mirrored_calls)
        payment_mirror = next(call for call in mirrored_calls if call["collection_name"] == "food_payments")
        self.assertEqual(payment_mirror["payload"]["payment_reference"], "PAY-LOCAL-1001")
        self.assertEqual(payment_mirror["payload"]["payment_id"], payment.id)
        self.assertEqual(payment_mirror["kwargs"]["upsert_filter"], {"payment_id": payment.id})

    def test_mirror_food_payment_uses_payment_id_as_primary_mongo_identity(self):
        payment = models.FoodPayment(
            student_id=7,
            amount=245.0,
            provider="razorpay",
            payment_reference="order_rzp_2001",
            provider_order_id="order_rzp_2001",
            status="created",
            order_state="created",
            payment_state="created",
            order_ids_json="[201,202]",
        )
        self.db.add(payment)
        self.db.commit()

        mirrored_calls: list[dict] = []

        def _capture_mirror(collection_name, payload, **kwargs):
            mirrored_calls.append(
                {
                    "collection_name": collection_name,
                    "payload": payload,
                    "kwargs": kwargs,
                }
            )
            return True

        with patch("app.routers.food.mirror_document", side_effect=_capture_mirror):
            _mirror_food_payment(
                payment,
                source="payment-intent",
                order_ids=[201, 202],
                extra={"subtotal_amount": 225.0, "delivery_fee": 10.0, "platform_fee": 10.0},
            )

        self.assertEqual(len(mirrored_calls), 1)
        payment_mirror = mirrored_calls[0]
        self.assertEqual(payment_mirror["collection_name"], "food_payments")
        self.assertEqual(payment_mirror["payload"]["payment_id"], payment.id)
        self.assertEqual(payment_mirror["payload"]["payment_reference"], "order_rzp_2001")
        self.assertEqual(payment_mirror["payload"]["order_ids"], [201, 202])
        self.assertEqual(payment_mirror["kwargs"]["upsert_filter"], {"payment_id": payment.id})

    def test_verify_payment_succeeds_when_mirror_backend_is_unavailable(self):
        self.db.add_all(
            [
                models.Student(
                    id=7,
                    name="Student Seven",
                    email="student7@example.com",
                    department="CSE",
                    semester=6,
                ),
                models.FoodItem(id=1, name="Wrap", price=120.0, is_active=True),
                models.BreakSlot(
                    id=1,
                    label="10:00 - 11:00",
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    max_orders=50,
                ),
            ]
        )
        self.db.flush()

        order = models.FoodOrder(
            id=111,
            student_id=7,
            food_item_id=1,
            slot_id=1,
            order_date=date(2026, 3, 24),
            quantity=1,
            unit_price=120.0,
            total_price=120.0,
            status=models.FoodOrderStatus.PLACED,
            payment_status="pending",
        )
        payment = models.FoodPayment(
            student_id=7,
            amount=120.0,
            provider="razorpay",
            payment_reference="PAY-LOCAL-1111",
            provider_order_id="order_rzp_1111",
            status="created",
            order_state="created",
            payment_state="created",
            order_ids_json="[111]",
        )
        self.db.add_all([order, payment])
        self.db.commit()

        payload = schemas.RazorpayVerifyRequest(
            razorpay_payment_id="pay_rzp_1111",
            razorpay_order_id="order_rzp_1111",
            razorpay_signature="sig_1111",
        )

        class _FakeRazorpayUtility:
            @staticmethod
            def verify_payment_signature(_payload):
                return True

        class _FakeRazorpayClient:
            utility = _FakeRazorpayUtility()

        with (
            patch("app.routers.food._get_razorpay_client", return_value=_FakeRazorpayClient()),
            patch("app.routers.food._mirror_document", side_effect=RuntimeError("mongo unavailable")),
            patch("app.routers.food._try_clear_food_cart", return_value=None),
        ):
            response = verify_payment(payload=payload, db=self.db, current_user=self._student_user())

        self.assertEqual(response.message, "Payment verified successfully")
        self.db.refresh(order)
        self.db.refresh(payment)
        self.assertEqual(order.status, models.FoodOrderStatus.VERIFIED)
        self.assertEqual(order.payment_status, "paid")
        self.assertEqual(payment.status, "paid")
        self.assertEqual(payment.provider_payment_id, "pay_rzp_1111")

    def test_report_payment_failure_succeeds_when_mirror_backend_is_unavailable(self):
        self.db.add_all(
            [
                models.Student(
                    id=7,
                    name="Student Seven",
                    email="student7@example.com",
                    department="CSE",
                    semester=6,
                ),
                models.FoodItem(id=1, name="Wrap", price=120.0, is_active=True),
                models.BreakSlot(
                    id=1,
                    label="10:00 - 11:00",
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    max_orders=50,
                ),
            ]
        )
        self.db.flush()

        order = models.FoodOrder(
            id=121,
            student_id=7,
            food_item_id=1,
            slot_id=1,
            order_date=date(2026, 3, 24),
            quantity=1,
            unit_price=120.0,
            total_price=120.0,
            status=models.FoodOrderStatus.PLACED,
            payment_status="created",
        )
        payment = models.FoodPayment(
            student_id=7,
            amount=120.0,
            provider="razorpay",
            payment_reference="PAY-LOCAL-1211",
            provider_order_id="order_rzp_1211",
            status="created",
            order_state="created",
            payment_state="created",
            order_ids_json="[121]",
        )
        self.db.add_all([order, payment])
        self.db.commit()

        payload = schemas.RazorpayFailureRequest(
            razorpay_order_id="order_rzp_1211",
            razorpay_payment_id="pay_rzp_failed_1211",
            error_code="BAD_REQUEST_ERROR",
            error_description="Payment authorization failed",
            error_reason="insufficient_funds",
        )

        with (
            patch("app.routers.food._fetch_razorpay_gateway_status", return_value=(None, None)),
            patch("app.routers.food._mirror_document", side_effect=RuntimeError("mongo unavailable")),
        ):
            response = report_payment_failure(payload=payload, db=self.db, current_user=self._student_user())

        self.assertEqual(response.message, "Payment failure recorded")
        self.db.refresh(order)
        self.db.refresh(payment)
        self.assertEqual(order.payment_status, "failed")
        self.assertEqual(payment.status, "failed")
        self.assertEqual(payment.payment_state, "failed")
        self.assertIn("insufficient_funds", str(payment.failed_reason or ""))

    def test_notify_order_status_tolerates_notification_mirror_failure(self):
        student = models.Student(
            id=7,
            name="Student Seven",
            email="student7@example.com",
            department="CSE",
            semester=6,
        )
        self.db.add_all(
            [
                student,
                models.FoodItem(id=1, name="Wrap", price=120.0, is_active=True),
                models.BreakSlot(
                    id=1,
                    label="10:00 - 11:00",
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    max_orders=50,
                ),
            ]
        )
        self.db.flush()

        order = models.FoodOrder(
            id=102,
            student_id=student.id,
            food_item_id=1,
            slot_id=1,
            order_date=date(2026, 3, 24),
            quantity=1,
            unit_price=120.0,
            total_price=120.0,
            status=models.FoodOrderStatus.PLACED,
            payment_status="pending",
        )
        self.db.add(order)
        self.db.flush()

        with patch("app.routers.food.mirror_document", side_effect=RuntimeError("mongo unavailable")):
            _notify_order_status(self.db, order, "Order being verified by shop")

        notifications = self.db.query(models.NotificationLog).filter(models.NotificationLog.student_id == student.id).all()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].message, "Order being verified by shop")

    def test_prepare_food_checkout_transaction_uses_row_locks_on_postgresql(self):
        lock_calls: list[tuple[str, tuple[int, ...]]] = []

        class _FakeQuery:
            def __init__(self, label):
                self.label = label

            def filter(self, *_args, **_kwargs):
                return self

            def with_for_update(self):
                return self

            def first(self):
                lock_calls.append((self.label, ()))
                return object()

            def all(self):
                lock_calls.append((self.label, ()))
                return [object()]

        class _FakeBind:
            class dialect:
                name = "postgresql"

        class _FakeSession:
            def __init__(self):
                self.executed_sql: list[str] = []

            def get_bind(self):
                return _FakeBind()

            def execute(self, stmt):
                self.executed_sql.append(str(stmt))

            def query(self, model):
                if model is models.BreakSlot:
                    return _FakeQuery("slot")
                if model is models.FoodMenuItem:
                    return _FakeQuery("menu")
                raise AssertionError(f"unexpected model: {model}")

        fake_db = _FakeSession()
        _prepare_food_checkout_transaction(fake_db, slot_id=1, menu_item_ids=[10, 11])

        self.assertEqual(fake_db.executed_sql, [])
        self.assertEqual(lock_calls, [("slot", ()), ("menu", ())])


if __name__ == "__main__":
    unittest.main()
