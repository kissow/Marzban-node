import unittest
from unittest.mock import Mock, patch

from device_activity import DeviceActivityTracker


class DeviceActivityTests(unittest.TestCase):
    def setUp(self):
        self.reader = Mock(return_value={"1.alice": {"uplink": 10, "downlink": 0}})
        self.tracker = DeviceActivityTracker(self.reader)
        self.clock = patch("device_activity.time.monotonic")
        self.time = self.clock.start()
        self.addCleanup(self.clock.stop)
        self.time.return_value = 0

    def sample(self, now, up=10, **users):
        self.time.return_value = now
        self.reader.return_value = {"1.alice": {"uplink": up}, **users}
        return self.tracker.snapshot()

    def test_first_sample_is_unknown_until_a_baseline_exists(self):
        result = self.sample(0)
        self.assertIsNone(result["active_users"])
        self.assertEqual(result["activity_reason"], "sampling_baseline")
        self.assertEqual(self.sample(10)["active_users"], 0)

    def test_activity_expires_in_a_rolling_window(self):
        self.sample(0)
        self.assertEqual(self.sample(10, 20)["active_users"], 1)
        self.assertEqual(self.sample(110, 20)["active_users"], 1)
        self.assertEqual(self.sample(131, 20)["active_users"], 0)

    def test_billing_reset_does_not_clear_other_users(self):
        self.sample(0, 100, **{"2.bob": {"uplink": 0}})
        result = self.sample(10, 5, **{"2.bob": {"uplink": 50}})
        self.assertEqual(result["active_users"], 2)

    def test_long_gap_and_restart_do_not_reuse_old_activity(self):
        self.sample(0)
        self.sample(10, 20)
        self.assertIsNone(self.sample(150, 500)["active_users"])
        self.tracker.reset()
        self.assertIsNone(self.sample(151, 0)["active_users"])

    def test_rpc_unavailable_is_unknown_not_zero(self):
        self.reader.side_effect = TimeoutError()
        self.assertIsNone(self.tracker.snapshot()["active_users"])
        self.assertEqual(self.tracker.snapshot()["activity_reason"], "stats_unavailable")

    def test_native_online_users_are_preferred_and_deduplicated(self):
        self.tracker = DeviceActivityTracker(self.reader, online_reader=lambda: ["alice", "alice", "bob"])
        result = self.tracker.snapshot()
        self.assertEqual(result["active_users"], 2)
        self.assertEqual(result["activity_scope"], "online_users")
        self.assertIsNone(result["active_users_window_seconds"])
        self.reader.assert_not_called()

    def test_empty_native_online_users_is_a_valid_zero(self):
        self.tracker = DeviceActivityTracker(self.reader, online_reader=lambda: [])
        self.assertEqual(self.tracker.snapshot()["active_users"], 0)
        self.reader.assert_not_called()

    def test_old_core_uses_observed_traffic_and_caches_samples(self):
        self.tracker = DeviceActivityTracker(self.reader, online_reader=lambda: None)
        self.sample(0)
        self.sample(1, 100)
        self.assertEqual(self.reader.call_count, 1)
        self.assertEqual(self.sample(6, 100)["active_users"], 1)
