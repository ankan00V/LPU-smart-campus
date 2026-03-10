import os
import unittest

import app.performance as performance


class PerformanceCapacityPlanTests(unittest.TestCase):
    def setUp(self):
        self._original = {
            "APP_CAPACITY_BASELINE_RPS": os.getenv("APP_CAPACITY_BASELINE_RPS"),
            "APP_CAPACITY_PER_NODE_RPS": os.getenv("APP_CAPACITY_PER_NODE_RPS"),
            "APP_CAPACITY_CURRENT_NODES": os.getenv("APP_CAPACITY_CURRENT_NODES"),
        }
        performance._SAMPLES.clear()

    def tearDown(self):
        for key, value in self._original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        performance._SAMPLES.clear()

    def test_build_capacity_plan_returns_recommendation(self):
        os.environ["APP_CAPACITY_PER_NODE_RPS"] = "10"
        os.environ["APP_CAPACITY_CURRENT_NODES"] = "2"

        for _ in range(120):
            performance.record_request_metric("/auth/me", "GET", 200, 120.0)

        report = performance.build_capacity_plan(
            window_minutes=15,
            expected_peak_rps=25.0,
            growth_percent=0.0,
            safety_factor=1.2,
        )
        self.assertGreaterEqual(report["recommended_nodes"], 1)
        self.assertIn("autoscale_recommended_action", report)
        self.assertIn("autoscale_thresholds_percent", report)
        self.assertIn("snapshot", report)
        self.assertIn("bucket_metrics", report["snapshot"])

    def test_enterprise_routes_are_bucketed_as_ops(self):
        performance.record_request_metric("/enterprise/dr/backups", "GET", 200, 1400.0)
        snapshot = performance.snapshot_sla(window_minutes=15)
        self.assertIn("ops", snapshot["bucket_metrics"])
        self.assertNotIn("default", snapshot["bucket_metrics"])
        self.assertEqual(snapshot["bucket_metrics"]["ops"]["target_p95_ms"], 5000.0)
        self.assertTrue(snapshot["bucket_metrics"]["ops"]["target_met"])


if __name__ == "__main__":
    unittest.main()
