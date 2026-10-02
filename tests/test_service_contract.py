import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException

from device_policy import DevicePolicyStore


# Importing the REST service normally probes the installed binary. Keep that
# probe isolated while exercising the real authentication and service methods.
core = Mock(started=True)
core.get_version.return_value = "26.3.27"
with patch("xray.XRayCore", return_value=core):
    spec = importlib.util.spec_from_file_location("test_rest_contract", Path(__file__).resolve().parents[1] / "rest_service.py")
    rest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rest)


class ServiceContractTests(unittest.TestCase):
    def setUp(self):
        self.service = rest.service
        self.service.connected = True
        self.service.session_id = uuid4()
        self.service.device_policies = DevicePolicyStore()
        self.service.activity = Mock()
        self.service.activity.snapshot.return_value = {"active_users": 2, "activity_scope": "online_users"}

    def test_wrong_missing_and_disconnected_sessions_are_rejected(self):
        for session in (uuid4(), None):
            with self.assertRaises(HTTPException) as error:
                self.service.set_device_policies(session, [])
            self.assertEqual(error.exception.status_code, 403)
        self.service.connected, self.service.session_id = False, None
        with self.assertRaises(HTTPException):
            self.service.device_activity(None)

    def test_policy_ack_changes_immediately_despite_resource_cache(self):
        session = self.service.session_id
        with patch.object(rest, "snapshot", return_value={"policy_count": 99}):
            self.service.set_device_policies(session, [{"user": "1.alice", "device_limit": 2}])
            self.assertEqual(self.service.health(session)["policy_count"], 1)
            self.service.set_device_policies(session, [])
            self.assertEqual(self.service.health(session)["policy_count"], 0)
            self.assertEqual(self.service.health(session)["active_users"], 2)

    def test_bad_policy_returns_422_and_keeps_previous_snapshot(self):
        session = self.service.session_id
        self.service.set_device_policies(session, [{"user": "1.alice", "device_limit": 2}])
        with self.assertRaises(HTTPException) as error:
            self.service.set_device_policies(session, [{"user": "1.alice", "device_limit": -1}])
        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(self.service.device_policies.metadata()["policy_count"], 1)
