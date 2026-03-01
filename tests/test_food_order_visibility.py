from datetime import date, time
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.auth_utils import CurrentUser
from app.routers.food import list_orders


class FoodOrderVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self._seed_orders()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _seed_orders(self):
        self.db.add_all(
            [
                models.Student(
                    id=1,
                    name="Student One",
                    email="student1@example.com",
                    department="CSE",
                    semester=6,
                ),
                models.Student(
                    id=2,
                    name="Student Two",
                    email="student2@example.com",
                    department="CSE",
                    semester=6,
                ),
                models.FoodItem(id=1, name="Paneer Wrap", price=120.0, is_active=True),
                models.BreakSlot(
                    id=1,
                    label="10:00 - 11:00",
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    max_orders=250,
                ),
            ]
        )
        self.db.flush()
        self.db.add_all(
            [
                models.FoodOrder(
                    student_id=1,
                    food_item_id=1,
                    slot_id=1,
                    order_date=date(2026, 2, 27),
                    quantity=1,
                    unit_price=120.0,
                    total_price=120.0,
                    status=models.FoodOrderStatus.PLACED,
                ),
                models.FoodOrder(
                    student_id=2,
                    food_item_id=1,
                    slot_id=1,
                    order_date=date(2026, 2, 27),
                    quantity=2,
                    unit_price=120.0,
                    total_price=240.0,
                    status=models.FoodOrderStatus.VERIFIED,
                ),
            ]
        )
        self.db.commit()

    @staticmethod
    def _user(*, role: models.UserRole, user_id: int, student_id: int | None, faculty_id: int | None = None):
        return CurrentUser(
            id=user_id,
            email=f"{role.value}{user_id}@example.com",
            role=role,
            student_id=student_id,
            faculty_id=faculty_id,
            alternate_email=None,
            primary_login_verified=True,
            is_active=True,
        )

    def test_faculty_cannot_view_student_order_history(self):
        faculty_user = self._user(role=models.UserRole.FACULTY, user_id=90, student_id=None, faculty_id=7)
        rows = list_orders(order_date=None, limit=100, db=self.db, current_user=faculty_user)
        self.assertEqual(rows, [])

    def test_student_sees_only_own_orders(self):
        student_user = self._user(role=models.UserRole.STUDENT, user_id=11, student_id=1)
        with patch("app.routers.food._sync_order_document", return_value=None):
            rows = list_orders(order_date=None, limit=100, db=self.db, current_user=student_user)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].student_id, 1)

    def test_admin_can_view_all_orders(self):
        admin_user = self._user(role=models.UserRole.ADMIN, user_id=1, student_id=None)
        with patch("app.routers.food._sync_order_document", return_value=None):
            rows = list_orders(order_date=None, limit=100, db=self.db, current_user=admin_user)
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
