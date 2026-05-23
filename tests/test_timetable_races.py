import unittest
from unittest import mock

from sqlalchemy.exc import IntegrityError

from app.routers.attendance import _get_or_create_sql_row


class DefaultTimetableRaceSafetyTests(unittest.TestCase):
    def test_reuses_existing_row_after_duplicate_insert_race(self):
        session = mock.Mock()
        savepoint = mock.Mock()
        session.begin_nested.return_value = savepoint
        session.flush.side_effect = IntegrityError(
            "INSERT INTO faculty ...",
            {"email": "ravindra.yadav@lpu.in"},
            Exception("duplicate key value violates unique constraint"),
        )

        created_row = object()
        existing_row = object()
        lookup = mock.Mock(side_effect=[None, existing_row])
        factory = mock.Mock(return_value=created_row)

        row, was_created = _get_or_create_sql_row(
            session,
            lookup=lookup,
            factory=factory,
        )

        self.assertIs(row, existing_row)
        self.assertFalse(was_created)
        session.add.assert_called_once_with(created_row)
        savepoint.rollback.assert_called_once()
        savepoint.commit.assert_not_called()

    def test_creates_row_without_retry_when_unique_conflict_does_not_happen(self):
        session = mock.Mock()
        savepoint = mock.Mock()
        session.begin_nested.return_value = savepoint

        created_row = object()
        lookup = mock.Mock(return_value=None)
        factory = mock.Mock(return_value=created_row)

        row, was_created = _get_or_create_sql_row(
            session,
            lookup=lookup,
            factory=factory,
        )

        self.assertIs(row, created_row)
        self.assertTrue(was_created)
        session.add.assert_called_once_with(created_row)
        session.flush.assert_called_once()
        savepoint.commit.assert_called_once()
        savepoint.rollback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
