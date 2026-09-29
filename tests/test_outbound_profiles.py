import json
import os
import subprocess
import unittest

from outbound_profiles import OutboundConfigError, apply_managed_outbounds


class ManagedOutboundTests(unittest.TestCase):
    def test_http_without_credentials(self):
        config = {"outbounds": [], "marzban_node_extensions": {"outbounds": [
            {"tag": "residential", "protocol": "http", "server": "proxy.example.net", "port": 8080}
        ]}}
        apply_managed_outbounds(config)
        self.assertEqual(config["outbounds"][0]["settings"],
                         {"address": "proxy.example.net", "port": 8080})

    def test_http_default_routes_only_tcp(self):
        config = {"outbounds": [{"tag": "direct", "protocol": "freedom"}],
                  "routing": {"rules": [{"type": "field", "network": "tcp", "outboundTag": "direct"}]},
                  "marzban_node_extensions": {"outbounds": [
                      {"tag": "residential", "protocol": "http", "server": "proxy.example.net", "port": 8080}
                  ], "default_outbound_tag": "residential"}}
        apply_managed_outbounds(config)
        self.assertEqual(config["routing"]["rules"][0]["network"], "tcp")
        self.assertEqual(config["routing"]["rules"][0]["outboundTag"], "residential")
        self.assertEqual(config["routing"]["rules"][1]["outboundTag"], "direct")

    def test_managed_default_route_and_restore_direct(self):
        config = {"outbounds": [{"tag": "direct", "protocol": "freedom"}],
                  "routing": {"rules": []},
                  "marzban_node_extensions": {"outbounds": [
                      {"tag": "residential", "protocol": "socks", "server": "proxy.example.net", "port": 1080}
                  ], "default_outbound_tag": "residential"}}
        apply_managed_outbounds(config)
        self.assertEqual(config["routing"]["rules"][0]["outboundTag"], "residential")
        restored = {"outbounds": [{"tag": "direct", "protocol": "freedom"}], "routing": {"rules": []}}
        apply_managed_outbounds(restored)
        self.assertEqual(restored["routing"]["rules"], [])

    def test_default_keeps_specific_rules_ahead_and_precedes_fallback(self):
        config = {"outbounds": [{"tag": "direct", "protocol": "freedom"}],
                  "routing": {"rules": [
                      {"type": "field", "domain": ["example.com"], "outboundTag": "direct"},
                      {"type": "field", "outboundTag": "direct"},
                  ]},
                  "marzban_node_extensions": {"outbounds": [
                      {"tag": "residential", "protocol": "socks", "server": "proxy.example.net", "port": 1080}
                  ], "default_outbound_tag": "residential"}}
        apply_managed_outbounds(config)
        self.assertEqual([rule["outboundTag"] for rule in config["routing"]["rules"]],
                         ["direct", "residential", "direct"])

    def test_stock_config_without_extension_is_unchanged(self):
        config = {"outbounds": [{"tag": "direct", "protocol": "freedom"}]}
        original = {"outbounds": [{"tag": "direct", "protocol": "freedom"}]}
        apply_managed_outbounds(config)
        self.assertEqual(config, original)

    def test_adds_authenticated_socks_outbound_without_exposing_extension(self):
        config = {
            "outbounds": [{"tag": "direct", "protocol": "freedom"}],
            "marzban_node_extensions": {"outbounds": [{
                "tag": "residential-a", "protocol": "socks",
                "server": "proxy.example.net", "port": 1080,
                "username": "account", "password": "secret",
            }]},
        }
        apply_managed_outbounds(config)
        self.assertNotIn("marzban_node_extensions", config)
        self.assertEqual(
            config["outbounds"][1]["settings"],
            {"address": "proxy.example.net", "port": 1080, "user": "account", "pass": "secret"},
        )

    def test_rejects_two_outbounds_for_one_node(self):
        config = {
            "outbounds": [{"tag": "direct", "protocol": "freedom"}],
            "marzban_node_extensions": {"outbounds": [
                {"tag": "residential-a", "protocol": "http", "server": "proxy.example.net", "port": 8080},
                {"tag": "residential-a", "protocol": "socks", "server": "proxy.example.net", "port": 1080},
            ]},
        }
        with self.assertRaisesRegex(OutboundConfigError, "at most one profile"):
            apply_managed_outbounds(config)

    def test_rejects_collision_with_existing_outbound(self):
        config = {
            "outbounds": [{"tag": "direct", "protocol": "freedom"}],
            "marzban_node_extensions": {"outbounds": [{
                "tag": "direct", "protocol": "http", "server": "proxy.example.net", "port": 8080,
            }]},
        }
        with self.assertRaisesRegex(OutboundConfigError, "duplicate outbound tag"):
            apply_managed_outbounds(config)

    def test_default_route_targets_existing_outbound(self):
        config = {
            "outbounds": [{"tag": "direct", "protocol": "freedom"}],
            "routing": {"rules": []},
            "marzban_node_extensions": {"default_outbound_tag": "direct"},
        }
        apply_managed_outbounds(config)
        self.assertEqual(config["routing"]["rules"][0]["outboundTag"], "direct")

    def test_rejects_unknown_default_outbound(self):
        config = {
            "outbounds": [{"tag": "direct", "protocol": "freedom"}],
            "marzban_node_extensions": {"default_outbound_tag": "missing"},
        }
        with self.assertRaisesRegex(OutboundConfigError, "default outbound tag does not exist"):
            apply_managed_outbounds(config)


@unittest.skipUnless(os.environ.get("XRAY_TEST_BINARY"), "XRAY_TEST_BINARY is not configured")
class XRayConfigValidationTests(unittest.TestCase):
    def test_http_and_socks_configs_pass_real_xray_parser(self):
        for protocol in ("http", "socks"):
            for authenticated in (False, True):
                with self.subTest(protocol=protocol, authenticated=authenticated):
                    profile = {"tag": "residential", "protocol": protocol,
                               "server": "proxy.example.net", "port": 8080}
                    if authenticated:
                        profile.update({"username": "alice", "password": "secret"})
                    config = {
                        "inbounds": [{"tag": "test-inbound", "listen": "127.0.0.1", "port": 10999,
                                      "protocol": "socks", "settings": {"auth": "noauth"}}],
                        "outbounds": [{"tag": "direct", "protocol": "freedom"}],
                        "routing": {"rules": []},
                        "marzban_node_extensions": {"outbounds": [profile], "default_outbound_tag": "residential"},
                    }
                    apply_managed_outbounds(config)
                    result = subprocess.run(
                        [os.environ["XRAY_TEST_BINARY"], "run", "-test", "-config", "stdin:"],
                        input=json.dumps(config), text=True, capture_output=True, timeout=20, check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
