import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.realtime_bus import user_scopes


class RealtimeScopeResolutionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        import app.database as database_module

        self._original_session_local = database_module.SessionLocal
        database_module.SessionLocal = self.SessionLocal

    def tearDown(self):
        import app.database as database_module

        database_module.SessionLocal = self._original_session_local
        self.engine.dispose()

    def test_owner_user_scopes_include_owned_shop_ids(self):
        db = self.SessionLocal()
        try:
            owner = models.AuthUser(
                id=501,
                email="owner@example.com",
                password_hash="hash",
                role=models.UserRole.OWNER,
                is_active=True,
            )
            owned_shop = models.FoodShop(
                id=301,
                name="North Plaza Cafe",
                block="Block 41",
                owner_user_id=501,
                is_active=True,
            )
            other_shop = models.FoodShop(
                id=302,
                name="South Plaza Cafe",
                block="Block 34",
                owner_user_id=999,
                is_active=True,
            )
            db.add_all([owner, owned_shop, other_shop])
            db.commit()
        finally:
            db.close()

        owner_user = self.SessionLocal().get(models.AuthUser, 501)
        scopes = user_scopes(owner_user)

        self.assertIn("role:owner", scopes)
        self.assertIn("user:501", scopes)
        self.assertIn("shop:301", scopes)
        self.assertNotIn("shop:302", scopes)


if __name__ == "__main__":
    unittest.main()
