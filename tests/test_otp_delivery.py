import os
import unittest
from unittest import mock

from app import otp_delivery


class OTPDeliveryTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_assert_ready_rejects_debug_mode(self):
        os.environ["OTP_DELIVERY_MODE"] = "debug"
        with self.assertRaises(RuntimeError):
            otp_delivery.assert_otp_delivery_ready()

    @mock.patch("app.otp_delivery.smtplib.SMTP")
    def test_assert_ready_verifies_smtp_login(self, smtp_cls):
        os.environ["OTP_DELIVERY_MODE"] = "smtp"
        os.environ["OTP_SMTP_HOST"] = "smtp.gmail.com"
        os.environ["OTP_SMTP_PORT"] = "587"
        os.environ["OTP_SMTP_USERNAME"] = "campus@example.com"
        os.environ["OTP_SMTP_PASSWORD"] = "abcd efgh ijkl mnop"
        os.environ["OTP_SMTP_STARTTLS"] = "true"
        os.environ["OTP_SMTP_USE_SSL"] = "false"
        os.environ["OTP_FROM_EMAIL"] = "campus@example.com"

        server = smtp_cls.return_value.__enter__.return_value
        server.noop.return_value = (250, b"OK")

        mode = otp_delivery.assert_otp_delivery_ready(verify_connection=True)

        self.assertEqual(mode, "smtp")
        smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=15)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("campus@example.com", "abcdefghijklmnop")
        server.noop.assert_called_once()

    @mock.patch("app.otp_delivery.smtplib.SMTP")
    def test_send_transactional_email_uses_smtp_transport(self, smtp_cls):
        os.environ["OTP_DELIVERY_MODE"] = "smtp"
        os.environ["OTP_SMTP_HOST"] = "smtp.gmail.com"
        os.environ["OTP_SMTP_PORT"] = "587"
        os.environ["OTP_SMTP_USERNAME"] = "campus@example.com"
        os.environ["OTP_SMTP_PASSWORD"] = "abcdefghijklmnop"
        os.environ["OTP_SMTP_STARTTLS"] = "true"
        os.environ["OTP_SMTP_USE_SSL"] = "false"
        os.environ["OTP_FROM_EMAIL"] = "campus@example.com"

        server = smtp_cls.return_value.__enter__.return_value

        result = otp_delivery.send_transactional_email(
            "faculty@example.com",
            subject="Attendance recovery action required",
            body="Review the recovery plan.",
        )

        self.assertEqual(result, {"channel": "smtp-email"})
        smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=15)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("campus@example.com", "abcdefghijklmnop")
        server.send_message.assert_called_once()
        message = server.send_message.call_args.args[0]
        self.assertEqual(message["To"], "faculty@example.com")
        self.assertEqual(message["Subject"], "Attendance recovery action required")
