"""Authenticated relay snapshots and protocol serialization, no production data."""
import copy
import asyncio
import json
import threading
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from relay_manager import CAPABILITY, RelayManager
import test_service_contract as bootstrap
from rpyc_service import XrayService
import rpyc
from rpyc.utils.server import ThreadedServer


class Runtime:
    def __init__(self):
        self.profiles, self.occupied, self.fail, self.last_error = [], set(), False, None
    @property
    def running(self):
        return bool(self.profiles)
    def occupied_ports(self):
        return self.occupied
    def snapshot(self):
        return copy.deepcopy(self.profiles)
    def apply(self, profiles):
        if self.fail:
            raise RuntimeError("test bind failure")
        self.profiles = copy.deepcopy(profiles)
    def stop(self):
        self.profiles = []


class RelayManagerTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.manager = RelayManager(self.runtime)
        self.item = {"node_id": 2, "listen_port": 18443, "target_address": "node2.test", "target_port": 8443}

    def test_json_native_snapshots_ack_and_explicit_clear(self):
        result = self.manager.replace([self.item])
        self.assertEqual(result["capability"], CAPABILITY)
        self.assertTrue(result["running"])
        self.assertEqual(result["profiles"], [self.item])
        self.assertEqual(self.manager.replace(json.dumps([self.item])), result)
        self.assertEqual(self.manager.replace([])["profiles"], [])
        self.assertFalse(self.manager.state()["running"])

    def test_invalid_schema_addresses_ranges_and_duplicates_do_not_replace(self):
        self.manager.replace([self.item])
        values = [None, {}, "bad-json", [self.item, self.item], [{**self.item, "config": "arbitrary"}],
                  [{**self.item, "node_id": True}], [{**self.item, "listen_port": 62050}],
                  [{**self.item, "listen_port": 62051}], [{**self.item, "listen_port": 80}],
                  [{**self.item, "target_port": 65536}], [{**self.item, "target_port": True}],
                  [{**self.item, "target_address": "127.0.0.1"}], [{**self.item, "target_address": "https://node.test"}],
                  [{**self.item, "target_address": {}}], [{**self.item, "target_port": 18443}]]
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.manager.replace(value)
            self.assertEqual(self.runtime.profiles, [self.item])

    def test_other_local_listeners_are_reserved_and_failure_keeps_previous(self):
        self.manager.replace([self.item])
        self.runtime.occupied = {19000}
        with self.assertRaises(ValueError):
            self.manager.replace([{**self.item, "listen_port": 19000}])
        self.assertIn(19000, self.manager.status()["occupied_ports"])
        self.runtime.fail = True
        with self.assertRaisesRegex(RuntimeError, "bind failure"):
            self.manager.replace([{**self.item, "listen_port": 19001}])
        self.assertEqual(self.runtime.profiles, [self.item])

    def test_hundreds_of_targets_have_distinct_fixed_ports_and_atomic_bounds(self):
        profiles = [{**self.item, "node_id": n + 1, "listen_port": 18443 + n, "target_address": f"node{n}.test"} for n in range(200)]
        self.assertEqual(len(self.manager.replace(profiles)["profiles"]), 200)
        with self.assertRaises(ValueError):
            self.manager.replace(profiles * 3)
        self.assertEqual(len(self.manager.state()["profiles"]), 200)


class RelayServiceTests(unittest.TestCase):
    def setUp(self):
        self.rest = bootstrap.rest.service
        self.rest.core = Mock(started=True)
        self.rest.connected, self.rest.session_id = True, uuid4()
        self.rest.relays = RelayManager(Runtime())
        self.item = {"node_id": 2, "listen_port": 18443, "target_address": "node2.test", "target_port": 8443}

    def test_rest_authentication_and_service_registration(self):
        paths = {route.path for route in self.rest.router.routes}
        self.assertTrue({"/relays", "/relays/status"} <= paths)
        for session in (None, uuid4()):
            for method, args in ((self.rest.relay_status, (session,)), (self.rest.set_relays, (session, [self.item]))):
                with self.assertRaises(HTTPException) as error:
                    method(*args)
                self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(self.rest.relays.state()["profiles"], [])

    def test_rest_native_ack_errors_and_core_not_started(self):
        self.assertEqual(self.rest.set_relays(self.rest.session_id, [self.item])["profiles"], [self.item])
        self.rest.relays.runtime.fail = True
        with self.assertRaises(HTTPException) as error:
            self.rest.set_relays(self.rest.session_id, [])
        self.assertEqual(error.exception.status_code, 409)
        self.rest.relays.runtime.fail = False
        with self.assertRaises(HTTPException) as error:
            self.rest.set_relays(self.rest.session_id, [{**self.item, "node_id": True}])
        self.assertEqual(error.exception.status_code, 422)
        self.rest.core.started = False
        with self.assertRaises(HTTPException) as error:
            self.rest.set_relays(self.rest.session_id, [self.item])
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.rest.set_relays(self.rest.session_id, [])["profiles"], [])

    def test_rest_real_asgi_body_and_wrong_session_do_not_apply(self):
        def request(body):
            raw, messages = json.dumps(body).encode(), []
            scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
                     "scheme": "https", "path": "/relays", "raw_path": b"/relays", "query_string": b"", "root_path": "",
                     "server": ("node.test", 62050), "client": ("192.0.2.1", 1234), "headers": [(b"content-type", b"application/json")]}
            async def receive():
                return {"type": "http.request", "body": raw, "more_body": False}
            async def send(message):
                messages.append(message)
            asyncio.run(bootstrap.rest.app(scope, receive, send))
            return next(m['status'] for m in messages if m['type'] == 'http.response.start'), json.loads(b''.join(m.get('body', b'') for m in messages))
        self.assertEqual(request({'session_id': str(uuid4()), 'profiles': [self.item]})[0], 403)
        self.assertEqual(self.rest.relays.state()['profiles'], [])
        status, result = request({'session_id': str(self.rest.session_id), 'profiles': [self.item]})
        self.assertEqual(status, 200)
        self.assertEqual(result['profiles'], [self.item])
        self.assertEqual(request({'session_id': str(self.rest.session_id), 'profiles': [{**self.item, 'node_id': True}]})[0], 422)
        self.assertEqual(self.rest.relays.state()['profiles'], [self.item])

    def test_rest_session_takeover_and_disconnect_clear_relay_not_new_certificates(self):
        self.rest.set_relays(self.rest.session_id, [self.item])
        old = self.rest.session_id
        self.rest.activity = Mock()
        self.rest.connect(Mock(client=Mock(host="192.0.2.1")))
        self.assertNotEqual(self.rest.session_id, old)
        self.assertEqual(self.rest.relays.state()["profiles"], [])
        self.rest.set_relays(self.rest.session_id, [self.item])
        self.rest.disconnect()
        self.assertEqual(self.rest.relays.state()["profiles"], [])

    def test_rpyc_json_roundtrip_and_cleanup(self):
        remote = XrayService()
        remote.core = Mock(started=True)
        remote.relays = RelayManager(Runtime())
        wire = json.dumps([self.item])
        ack = json.loads(remote.set_relays(wire))
        self.assertEqual(ack["profiles"], [self.item])
        self.assertEqual(json.loads(remote.fetch_relay_status())["capability"], CAPABILITY)
        remote.stop()
        self.assertEqual(json.loads(remote.set_relays("[]"))["profiles"], [])
        self.assertEqual(json.loads(remote.fetch_relay_status())["core_started"], False)

    def test_real_rpyc_socket_serializes_nested_snapshot_as_plain_json(self):
        # Real local RPyC transport with the production exposed methods. This
        # verifies serialization, not TLS authentication (unchanged elsewhere).
        remote = XrayService()
        remote.core = Mock(started=True)
        remote.relays = RelayManager(Runtime())
        server = ThreadedServer(remote, hostname="127.0.0.1", port=0)
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        connection = None
        try:
            connection = rpyc.connect("127.0.0.1", server.port)
            result = rpyc.async_(connection.root.set_relays)(json.dumps([self.item]))
            result.set_expiry(5)
            result.wait()
            self.assertIs(type(result.value), str)
            ack = json.loads(result.value)
            self.assertEqual(ack["profiles"], [self.item])
            self.assertIs(type(ack["profiles"][0]), dict)
            status = json.loads(connection.root.fetch_relay_status())
            self.assertTrue(status["core_started"])
            self.assertEqual(status["capability"], CAPABILITY)
        finally:
            if connection:
                connection.close()
            server.close()
            thread.join(timeout=5)
        self.assertEqual(remote.relays.state()["profiles"], [])


if __name__ == "__main__":
    unittest.main()
