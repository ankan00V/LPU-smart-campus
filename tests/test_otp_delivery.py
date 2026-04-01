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

    @mock.patch("app.otp_delivery.pytime.sleep")
    @mock.patch("app.otp_delivery.smtplib.SMTP")
    def test_assert_ready_retries_transient_smtp_verification_failure(self, smtp_cls, sleep_mock):
        os.environ["OTP_DELIVERY_MODE"] = "smtp"
        os.environ["OTP_SMTP_HOST"] = "smtp.gmail.com"
        os.environ["OTP_SMTP_PORT"] = "587"
        os.environ["OTP_SMTP_USERNAME"] = "campus@example.com"
        os.environ["OTP_SMTP_PASSWORD"] = "abcd efgh ijkl mnop"
        os.environ["OTP_SMTP_STARTTLS"] = "true"
        os.environ["OTP_SMTP_USE_SSL"] = "false"
        os.environ["OTP_FROM_EMAIL"] = "campus@example.com"
        os.environ["OTP_SMTP_VERIFY_MAX_ATTEMPTS"] = "2"
        os.environ["OTP_SMTP_VERIFY_RETRY_DELAY_SECONDS"] = "0"

        server = smtp_cls.return_value.__enter__.return_value
        server.ehlo.side_effect = [
            otp_delivery.smtplib.SMTPServerDisconnected("Connection unexpectedly closed: The read operation timed out"),
            (250, b"OK"),
            (250, b"OK"),
        ]
        server.noop.return_value = (250, b"OK")

        mode = otp_delivery.assert_otp_delivery_ready(verify_connection=True)

        self.assertEqual(mode, "smtp")
        self.assertEqual(smtp_cls.call_count, 2)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("campus@example.com", "abcdefghijklmnop")
        server.noop.assert_called_once()
        sleep_mock.assert_not_called()

    @mock.patch("app.otp_delivery.smtplib.SMTP")
    def test_send_login_otp_prepares_starttls_session_before_delivery(self, smtp_cls):
        os.environ["OTP_DELIVERY_MODE"] = "smtp"
        os.environ["OTP_SMTP_HOST"] = "smtp.gmail.com"
        os.environ["OTP_SMTP_PORT"] = "587"
        os.environ["OTP_SMTP_USERNAME"] = "campus@example.com"
        os.environ["OTP_SMTP_PASSWORD"] = "abcd efgh ijkl mnop"
        os.environ["OTP_SMTP_STARTTLS"] = "true"
        os.environ["OTP_SMTP_USE_SSL"] = "false"
        os.environ["OTP_FROM_EMAIL"] = "campus@example.com"

        server = smtp_cls.return_value.__enter__.return_value

        payload = otp_delivery.send_login_otp("student@example.com", "123456")

        self.assertEqual(payload, {"channel": "smtp-email"})
        smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=15)
        self.assertEqual(server.ehlo.call_count, 2)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("campus@example.com", "abcdefghijklmnop")
        server.send_message.assert_called_once()
