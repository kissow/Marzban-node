import unittest
from unittest.mock import patch

import health


class HealthSnapshotTests(unittest.TestCase):
    def tearDown(self):
        health._cached_at = 0
        health._cached_snapshot = None
        health._cpu_sample = None

    def test_snapshot_reports_runtime_scopes_and_nonnegative_values(self):
        with patch.object(health, "_read_text", return_value=None), patch.object(
            health.shutil, "disk_usage", return_value=type(
                "DiskUsage", (), {"total": 100, "used": 40}
            )()
        ):
            sample = health.snapshot()

        self.assertEqual(sample["source"], "node-runtime")
        self.assertEqual(sample["disk_total_bytes"], 100)
        self.assertEqual(sample["disk_used_bytes"], 40)
        self.assertEqual(sample["disk_path"], "/")
        self.assertEqual(sample["cpu_scope"], "node-os")
        self.assertIsNone(sample["memory_total_bytes"])

    def test_cpu_requires_two_valid_samples(self):
        with patch.object(health, "_read_text", side_effect=(
            "cpu 100 0 100 800 0", "cpu 120 0 110 870 0"
        )):
            self.assertIsNone(health._cpu_percent())
            self.assertEqual(health._cpu_percent(), 30.0)

    def test_memory_prefers_finite_cgroup_limit(self):
        values = {
            "/sys/fs/cgroup/memory.max": "1000",
            "/sys/fs/cgroup/memory.current": "400",
        }
        with patch.object(health, "_read_text", side_effect=lambda path: values.get(path)):
            self.assertEqual(health._memory_bytes(), (1000, 400, "node-cgroup"))

    def test_snapshot_is_cached(self):
        with patch.object(health, "_read_text", return_value=None), patch.object(
            health.shutil, "disk_usage", return_value=type(
                "DiskUsage", (), {"total": 100, "used": 40}
            )()
        ) as disk_usage:
            health.snapshot()
            health.snapshot()
        self.assertEqual(disk_usage.call_count, 1)


if __name__ == "__main__":
    unittest.main()
