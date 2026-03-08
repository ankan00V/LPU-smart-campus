import os
import unittest
from unittest import mock

from app import mongo


class _FakeSRVRecord:
    def __init__(self, target: str, port: int = 27017):
        self.target = target
        self.port = port


class _FakeTXTRecord:
    def __init__(self, value: str):
        self._value = value

    def to_text(self) -> str:
        return f'"{self._value}"'


class _FakeResolver:
    def __init__(self):
        self.nameservers = []
        self.lifetime = 0
        self.timeout = 0

    def resolve(self, name: str, record_type: str):
        if record_type == "SRV":
            self.last_srv_name = name
            return [
                _FakeSRVRecord("ac-navwpai-shard-00-00.amxxiyi.mongodb.net."),
                _FakeSRVRecord("ac-navwpai-shard-00-01.amxxiyi.mongodb.net."),
                _FakeSRVRecord("ac-navwpai-shard-00-02.amxxiyi.mongodb.net."),
            ]
        if record_type == "TXT":
            self.last_txt_name = name
            return [_FakeTXTRecord("authSource=admin&replicaSet=atlas-ynea0w-shard-0")]
        raise AssertionError(f"Unexpected record type: {record_type}")


class MongoUriResolutionTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    @mock.patch("app.mongo.dns_resolver")
    def test_hostname_fallback_uri_generated_from_srv(self, mock_dns_resolver):
        fake_resolver = _FakeResolver()
        mock_dns_resolver.Resolver.return_value = fake_resolver
        os.environ["MONGO_DNS_NAMESERVERS"] = "1.1.1.1,8.8.8.8"
        uri = (
            "mongodb+srv://user:pass@lpu.amxxiyi.mongodb.net/"
            "?retryWrites=true&w=majority&authSource=admin"
        )

        fallback = mongo._mongo_hostname_fallback_uri(uri)

        self.assertIsNotNone(fallback)
        self.assertIn("mongodb://user:pass@", fallback)
        self.assertIn("ac-navwpai-shard-00-00.amxxiyi.mongodb.net:27017", fallback)
        self.assertIn("ac-navwpai-shard-00-01.amxxiyi.mongodb.net:27017", fallback)
        self.assertIn("ac-navwpai-shard-00-02.amxxiyi.mongodb.net:27017", fallback)
        self.assertIn("replicaSet=atlas-ynea0w-shard-0", fallback)
        self.assertIn("authSource=admin", fallback)
        self.assertIn("retryWrites=true", fallback)
        self.assertIn("tls=true", fallback)
        self.assertEqual(fake_resolver.last_srv_name, "_mongodb._tcp.lpu.amxxiyi.mongodb.net")
        self.assertEqual(fake_resolver.last_txt_name, "lpu.amxxiyi.mongodb.net")

    def test_hostname_fallback_uri_ignored_for_non_srv_scheme(self):
        fallback = mongo._mongo_hostname_fallback_uri("mongodb://user:pass@localhost:27017/test")
        self.assertIsNone(fallback)
