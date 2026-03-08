import json
import unittest
from types import SimpleNamespace
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models, schemas
from app.routers.remedial import _verify_remedial_face_payload


class RemedialProfileMediaStorageTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_face_verification_uses_object_storage_profile_photo(self):
        student = models.Student(
            id=11,
            name="Media Student",
            email="media.student@example.com",
            registration_number="REG-11",
            parent_email=None,
            section="P132",
            department="CSE",
            semester=5,
            profile_photo_data_url=None,
            profile_photo_object_key="student-profile/2026/03/04/photo.jpg",
            profile_face_template_json=None,
            enrollment_video_template_json=json.dumps({"embeddings": [[0.1, 0.2, 0.3, 0.4]]}),
        )
        payload = schemas.RemedialAttendanceMark(
            remedial_code="REM2026A",
            student_id=11,
            selfie_photo_data_url="data:image/jpeg;base64,SELFIEA",
            selfie_frames_data_urls=[
                "data:image/jpeg;base64,SELFIEA",
                "data:image/jpeg;base64,SELFIEB",
                "data:image/jpeg;base64,SELFIEC",
                "data:image/jpeg;base64,SELFIED",
                "data:image/jpeg;base64,SELFIEE",
                "data:image/jpeg;base64,SELFIEF",
            ],
        )
        class_row = SimpleNamespace(id=9001)

        with mock.patch(
            "app.routers.remedial.data_url_for_object",
            return_value="data:image/jpeg;base64,PROFILEA",
        ) as data_url_for_object, mock.patch(
            "app.routers.remedial.build_profile_face_template",
            return_value={"embeddings": [[0.8, 0.7, 0.6, 0.5]]},
        ), mock.patch(
            "app.routers.remedial.verify_face_sequence_opencv",
            return_value={
                "available": True,
                "match": True,
                "confidence": 0.98,
                "engine": "opencv-embedding",
                "reason": "verified",
            },
        ) as verify_face_sequence_opencv:
            primary_selfie, confidence, engine, reason = _verify_remedial_face_payload(
                db=self.db,
                student=student,
                payload=payload,
                class_row=class_row,
            )

        data_url_for_object.assert_called_once_with(self.db, "student-profile/2026/03/04/photo.jpg")
        verify_args, _verify_kwargs = verify_face_sequence_opencv.call_args
        self.assertEqual(verify_args[0], "data:image/jpeg;base64,PROFILEA")
        self.assertEqual(primary_selfie, "data:image/jpeg;base64,SELFIEA")
        self.assertGreaterEqual(confidence, 0.98)
        self.assertEqual(engine, "opencv-embedding")
        self.assertEqual(reason, "verified")


if __name__ == "__main__":
    unittest.main()
