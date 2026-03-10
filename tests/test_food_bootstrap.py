import unittest
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.food_bootstrap import FOOD_CATALOG_POLICY_KEY, bootstrap_food_hall_catalog


class FoodBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_bootstrap_skips_when_catalog_version_and_counts_match(self):
        with (
            mock.patch("app.food_bootstrap.mirror_document", return_value=True),
            mock.patch("app.food_bootstrap.mirror_event", return_value=True),
        ):
            first = bootstrap_food_hall_catalog(self.db)
            second = bootstrap_food_hall_catalog(self.db)

        self.assertFalse(first["skipped"])
        self.assertTrue(second["skipped"])
        self.assertEqual(first["after_counts"], second["after_counts"])
        state = (
            self.db.query(models.AdminPolicySetting)
            .filter(models.AdminPolicySetting.key == FOOD_CATALOG_POLICY_KEY)
            .first()
        )
        self.assertIsNotNone(state)

    def test_forced_bootstrap_runs_even_when_catalog_is_current(self):
        with (
            mock.patch("app.food_bootstrap.mirror_document", return_value=True),
            mock.patch("app.food_bootstrap.mirror_event", return_value=True),
        ):
            bootstrap_food_hall_catalog(self.db)
            forced = bootstrap_food_hall_catalog(self.db, force=True)

        self.assertFalse(forced["skipped"])
        self.assertGreaterEqual(int(forced["shops_updated"]), 1)
