import os
import unittest


os.environ["APP_RUNTIME_STRICT"] = "false"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite:///:memory:"

from app import mongo


class MongoStatusTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_srv_uri_reports_tls_enabled(self):
        os.environ["MONGO_URI"] = "mongodb+srv://example.mongodb.net/?retryWrites=true&w=majority"
        self.assertTrue(mongo._mongo_tls_enabled())

    def test_plain_local_uri_reports_tls_disabled(self):
        os.environ["MONGO_URI"] = "mongodb://127.0.0.1:27017"
        self.assertFalse(mongo._mongo_tls_enabled())

    def test_plain_uri_with_tls_query_reports_tls_enabled(self):
        os.environ["MONGO_URI"] = "mongodb://mongo:27017/?tls=true"
        self.assertTrue(mongo._mongo_tls_enabled())

