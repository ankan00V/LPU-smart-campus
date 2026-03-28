import unittest
from unittest import mock

from app.realtime_bus import RealtimeEventHub


class _FakeThread:
    def __init__(self, *, alive: bool = True) -> None:
        self._alive = alive
        self.join_calls: list[float | None] = []

    def is_alive(self) -> bool:
        return self._alive

    def join(self, timeout: float | None = None) -> None:
        self.join_calls.append(timeout)
        self._alive = False


class RealtimeHubLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_discards_dead_threads_before_spawning_new_listeners(self):
        hub = RealtimeEventHub()
        dead_thread = _FakeThread(alive=False)
        new_thread = _FakeThread(alive=True)
        hub._listener_threads = [dead_thread]

        with mock.patch("app.realtime_bus._start_backend_listeners", return_value=[new_thread]) as start_patch:
            await hub.start()

        start_patch.assert_called_once()
        self.assertEqual(hub._listener_threads, [new_thread])

    async def test_stop_joins_active_listener_threads_before_clearing_state(self):
        hub = RealtimeEventHub()
        active_thread = _FakeThread(alive=True)
        hub._listener_threads = [active_thread]
        subscriber_id, _queue = await hub.subscribe(scopes={"scope:all"}, topics={"*"})

        self.assertIn(subscriber_id, hub._subscribers)

        await hub.stop()

        self.assertEqual(active_thread.join_calls, [1.0])
        self.assertEqual(hub._listener_threads, [])
        self.assertEqual(hub._subscribers, {})


if __name__ == "__main__":
    unittest.main()
