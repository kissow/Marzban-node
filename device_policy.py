"""Shared, atomic validation for optional device policy snapshots."""

import hashlib
import json
import threading
from datetime import datetime, timezone


class DevicePolicyStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._metadata = {"policy_count": 0, "policy_synced_at": None,
                          "policy_revision": None,
                          "policy_enforcement": "subscription_request_and_node_credentials",
                          "direct_connection_enforced": True}
        self._policies = []

    def replace(self, policies):
        # JSON crosses RPyC as a plain string instead of mutable netrefs.
        if isinstance(policies, str):
            if len(policies) > 4_000_000:
                raise ValueError("Device policy snapshot is too large")
            policies = json.loads(policies)
        if not isinstance(policies, list) or len(policies) > 10000:
            raise ValueError("Invalid device policy snapshot")
        normalized, seen = [], set()
        for policy in policies:
            if not isinstance(policy, dict):
                raise ValueError("Each policy must be an object")
            user, limit = policy.get("user"), policy.get("device_limit", 0)
            mode, action = policy.get("device_limit_mode", "hwid"), policy.get("device_limit_action", "log_only")
            if not isinstance(user, str) or not 1 <= len(user) <= 128 or user in seen:
                raise ValueError("Invalid or duplicate policy user")
            if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100000:
                raise ValueError("Invalid device limit")
            if mode != "hwid" or action not in ("log_only", "reject_new"):
                raise ValueError("Unsupported device policy")
            seen.add(user)
            normalized.append({"user": user, "device_limit": limit,
                               "device_limit_mode": mode, "device_limit_action": action})
        normalized.sort(key=lambda policy: policy["user"])
        revision = hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
        with self._lock:
            self._policies = normalized
            self._metadata.update(policy_count=len(normalized), policy_revision=revision,
                                  policy_synced_at=datetime.now(timezone.utc).isoformat())
            return {"accepted": True, **self._metadata}

    def metadata(self):
        with self._lock:
            return dict(self._metadata)
