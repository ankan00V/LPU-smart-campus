from datetime import datetime, timedelta
import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.remedial import mark_remedial_attendance, validate_remedial_code


class RemedialAccessFallbackTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()
        self._seed()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _seed(self):
        now_dt = datetime.now().replace(second=0, microsecond=0)
        class_start = now_dt - timedelta(minutes=5)
        class_end = now_dt + timedelta(minutes=55)

        self.db.add_all(
            [
                models.Faculty(
                    id=1,
                    name="Faculty One",
                    email="faculty.one@example.com",
                    department="CSE",
                    section="P132",
                ),
                models.Course(
                    id=1,
                    code="CSE202",
                    title="OOPS PROGRAMMING",
                    faculty_id=1,
                ),
                models.Student(
                    id=1,
                    name="Student One",
                    email="student.one@example.com",
                    department="CSE",
                    semester=4,
                    section="P132",
                ),
                models.Student(
                    id=2,
                    name="Student Two",
                    email="student.two@example.com",
                    department="CSE",
                    semester=4,
                    section="P132",
                ),
                models.MakeUpClass(
                    id=1,
                    course_id=1,
                    faculty_id=1,
                    class_date=class_start.date(),
                    start_time=class_start.time(),
                    end_time=class_end.time(),
                    topic="Remedial OOPS",
                    sections_json=json.dumps(["P132"]),
                    class_mode="offline",
                    room_number="18-310",
                    online_link=None,
                    remedial_code="4C5X5OSK",
                    code_generated_at=now_dt - timedelta(minutes=6),
                    code_expires_at=now_dt + timedelta(minutes=20),
                    attendance_open_minutes=15,
                    scheduled_at=now_dt - timedelta(minutes=10),
                    is_active=True,
                    created_at=now_dt - timedelta(minutes=10),
                ),
                models.RemedialMessage(
                    id=1,
                    makeup_class_id=1,
                    faculty_id=1,
                    student_id=1,
                    section="P132",
                    remedial_code="4C5X5OSK",
                    message="Use code 4C5X5OSK",
                    created_at=now_dt - timedelta(minutes=1),
                ),
            ]
        )
        self.db.commit()

    def _student_user(self, student_id: int) -> models.AuthUser:
        return models.AuthUser(
            id=9000 + student_id,
            email=f"student.{student_id}@example.com",
            password_hash="x",
            role=models.UserRole.STUDENT,
            student_id=student_id,
            faculty_id=None,
            is_active=True,
        )

    def test_validate_and_mark_allow_targeted_student_without_enrollment(self):
        class_row = self.db.get(models.MakeUpClass, 1)
        class_row.sections_json = json.dumps([" p 132 "])
        self.db.commit()

        validate_out = validate_remedial_code(
            payload=schemas.RemedialCodeValidateRequest(remedial_code="4C5X5OSK"),
            db=self.db,
            current_user=self._student_user(1),
        )
        self.assertTrue(validate_out.valid)
        self.assertEqual(validate_out.class_id, 1)

        with patch("app.routers.remedial.mirror_document", return_value=None), patch(
            "app.routers.remedial.mirror_event", return_value=None
        ), patch(
            "app.routers.remedial._verify_remedial_face_payload",
            return_value=("data:image/jpeg;base64,AAAA", 0.98, "opencv-embedding", "verified"),
        ):
            mark_out = mark_remedial_attendance(
                payload=schemas.RemedialAttendanceMark(
                    remedial_code="4C5X5OSK",
                    student_id=1,
                    selfie_photo_data_url="data:image/jpeg;base64,AAAA",
                    selfie_frames_data_urls=[
                        "data:image/jpeg;base64,AAAA",
                        "data:image/jpeg;base64,AAAB",
                        "data:image/jpeg;base64,AAAC",
                        "data:image/jpeg;base64,AAAD",
                        "data:image/jpeg;base64,AAAE",
                    ],
                ),
                db=self.db,
                current_user=self._student_user(1),
            )
        self.assertIn("message", mark_out)
        self.assertEqual(
            self.db.query(models.RemedialAttendance)
            .filter(
                models.RemedialAttendance.makeup_class_id == 1,
                models.RemedialAttendance.student_id == 1,
            )
            .count(),
            1,
        )

    def test_validate_and_mark_reject_untargeted_student_without_enrollment(self):
        with self.assertRaises(HTTPException) as validate_err:
            validate_remedial_code(
                payload=schemas.RemedialCodeValidateRequest(remedial_code="4C5X5OSK"),
                db=self.db,
                current_user=self._student_user(2),
            )
        self.assertEqual(validate_err.exception.status_code, 403)

        with self.assertRaises(HTTPException) as mark_err:
            with patch("app.routers.remedial.mirror_document", return_value=None), patch(
                "app.routers.remedial.mirror_event", return_value=None
            ):
                mark_remedial_attendance(
                    payload=schemas.RemedialAttendanceMark(remedial_code="4C5X5OSK", student_id=2),
                    db=self.db,
                    current_user=self._student_user(2),
                )
        self.assertEqual(mark_err.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
