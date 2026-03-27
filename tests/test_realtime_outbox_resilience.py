import os
import unittest
from unittest import mock

from app.realtime_bus import RealtimeEventHub, _publish_backend_event, realtime_hub


class RealtimeOutboxResilienceTests(unittest.TestCase):
    def test_publish_backend_event_raises_when_all_backends_fail_even_in_non_strict_mode(self):
        with (
            mock.patch.dict(
                os.environ,
                {
                    "APP_RUNTIME_STRICT": "false",
                    "REALTIME_BACKENDS_REQUIRED": "false",
                },
                clear=False,
            ),
            mock.patch("app.realtime_bus._realtime_backends", return_value=["redis", "postgres"]),
            mock.patch("app.realtime_bus.publish_json", side_effect=RuntimeError("redis down")),
            mock.patch("app.realtime_bus._publish_postgres_event", side_effect=RuntimeError("postgres down")),
        ):
            with self.assertRaisesRegex(RuntimeError, "all backends"):
                _publish_backend_event({"id": "evt-fail-all"})

    def test_publish_backend_event_succeeds_when_one_backend_is_available(self):
        with (
            mock.patch.dict(
                os.environ,
                {
                    "APP_RUNTIME_STRICT": "true",
                    "REALTIME_BACKENDS_REQUIRED": "true",
                },
                clear=False,
            ),
            mock.patch("app.realtime_bus._realtime_backends", return_value=["redis", "postgres"]),
            mock.patch("app.realtime_bus.publish_json", side_effect=RuntimeError("redis down")),
            mock.patch("app.realtime_bus._publish_postgres_event", return_value=None) as postgres_publish,
        ):
            _publish_backend_event({"id": "evt-partial-success"})

        postgres_publish.assert_called_once()

    def test_publish_returns_success_when_required_backend_falls_back_to_outbox(self):
        event_type = "attendance.marked"

        with mock.patch("app.realtime_bus._publish_backend_event", side_effect=RuntimeError("redis down")), mock.patch(
            "app.realtime_bus._enqueue_realtime_outbox",
            return_value=True,
        ) as outbox_patch:
            realtime_hub.publish(
                event_type,
                payload={"student_id": 1},
                scopes={"student:1"},
                topics={"attendance"},
            )

        outbox_patch.assert_called_once()

    def test_publish_raises_when_required_backend_and_outbox_both_fail(self):
        with mock.patch("app.realtime_bus._publish_backend_event", side_effect=RuntimeError("redis down")), mock.patch(
            "app.realtime_bus._enqueue_realtime_outbox",
            return_value=False,
        ):
            with self.assertRaisesRegex(RuntimeError, "redis down"):
                realtime_hub.publish(
                    "attendance.marked",
                    payload={"student_id": 1},
                    scopes={"student:1"},
                    topics={"attendance"},
                )

    def test_publish_prebuilt_replays_to_local_subscribers_before_backend_echo(self):
        delivered = []

        async def _exercise() -> None:
            hub = RealtimeEventHub()
            hub.bind_loop(asyncio.get_running_loop())
            _subscriber_id, queue = await hub.subscribe(scopes={"student:1"}, topics={"messages"})

            event = {
                "id": "evt-local-replay",
                "origin": "instance-a",
                "event_type": "messages.support.updated",
                "source": "outbox",
                "actor": {},
                "payload": {"student_id": 1},
                "scopes": ["student:1"],
                "topics": ["messages"],
                "created_at": "2026-03-24T00:00:00+00:00",
            }

            with mock.patch("app.realtime_bus._publish_backend_event", return_value=None):
                hub.publish_prebuilt(event, allow_outbox=False)

            delivered.append(await asyncio.wait_for(queue.get(), timeout=1.0))

        import asyncio

        asyncio.run(_exercise())

        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0]["id"], "evt-local-replay")

    def test_publish_prebuilt_dedupes_backend_echo_after_local_replay(self):
        observed = []

        async def _exercise() -> None:
            hub = RealtimeEventHub()
            hub.bind_loop(asyncio.get_running_loop())
            _subscriber_id, queue = await hub.subscribe(scopes={"student:1"}, topics={"messages"})

            event = {
                "id": "evt-local-replay-dedupe",
                "origin": "instance-a",
                "event_type": "messages.support.updated",
                "source": "outbox",
                "actor": {},
                "payload": {"student_id": 1},
                "scopes": ["student:1"],
                "topics": ["messages"],
                "created_at": "2026-03-24T00:00:00+00:00",
            }

            with mock.patch("app.realtime_bus._publish_backend_event", return_value=None):
                hub.publish_prebuilt(event, allow_outbox=False)

            observed.append(await asyncio.wait_for(queue.get(), timeout=1.0))
            hub._on_backend_message(dict(event))
            try:
                observed.append(await asyncio.wait_for(queue.get(), timeout=0.1))
            except asyncio.TimeoutError:
                observed.append(None)

        import asyncio

        asyncio.run(_exercise())

        self.assertEqual(observed[0]["id"], "evt-local-replay-dedupe")
        self.assertIsNone(observed[1])


if __name__ == "__main__":
    unittest.main()
