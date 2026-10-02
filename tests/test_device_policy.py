import json
import unittest

from device_policy import DevicePolicyStore


class DevicePolicyTests(unittest.TestCase):
    def setUp(self):
        self.store = DevicePolicyStore()
        self.policy = {"user": "1.alice", "device_limit": 2,
                       "device_limit_mode": "hwid", "device_limit_action": "reject_new"}

    def test_snapshot_is_atomic_and_replaces_removed_users(self):
        result = self.store.replace([self.policy])
        self.assertTrue(result["accepted"])
        self.assertEqual(result["policy_count"], 1)
        self.assertTrue(result["direct_connection_enforced"])
        self.assertIsNotNone(result["policy_synced_at"])
        previous = self.store.metadata()
        for invalid in (False, -1, 100001, "2"):
            with self.assertRaises(ValueError):
                self.store.replace([{**self.policy, "device_limit": invalid}])
            self.assertEqual(self.store.metadata(), previous)
        self.assertEqual(self.store.replace([])["policy_count"], 0)

    def test_rpyc_json_contract_matches_rest_contract(self):
        rest = self.store.replace([self.policy])
        rpyc = self.store.replace(json.dumps([self.policy]))
        self.assertEqual(rest["policy_revision"], rpyc["policy_revision"])
        self.assertEqual(rest["policy_count"], rpyc["policy_count"])

    def test_duplicate_users_and_invalid_modes_are_rejected(self):
        for policies in ([self.policy, self.policy], [{**self.policy, "device_limit_mode": "ip"}],
                         [{**self.policy, "device_limit_action": "block_all"}], [1]):
            with self.assertRaises(ValueError):
                self.store.replace(policies)

    def test_only_policy_fields_survive_serialization(self):
        expected = self.store.replace([self.policy])["policy_revision"]
        extra = self.store.replace([{**self.policy, "password": "secret", "hwid": "raw-id"}])
        self.assertEqual(extra["policy_revision"], expected)
        self.assertNotIn("password", str(extra))
        self.assertNotIn("raw-id", str(extra))
