import json
from copy import deepcopy
import os
import subprocess
import unittest

from outbound_profiles import OutboundConfigError, apply_managed_outbounds


class ManagedOutboundTests(unittest.TestCase):
    def udp_config(self, mode="tcp_only", protocol="socks"):
        return {"outbounds": [{"tag": "direct", "protocol": "freedom"}],
                "dns": {"hosts": {"example.test": "192.0.2.1"}},
                "routing": {"rules": [{"type": "field", "inboundTag": ["api"], "outboundTag": "api"},
                                      {"type": "field", "outboundTag": "direct"}]},
                "marzban_node_extensions": {"outbounds": [{"tag": "residential", "protocol": protocol,
                    "server": "127.0.0.1", "port": 1080, "udp_mode": mode}], "default_outbound_tag": "residential"}}

    def test_tcp_only_dns_tunnels_and_other_udp_blocks(self):
        config = self.udp_config()
        apply_managed_outbounds(config)
        outbounds = {item["tag"]: item for item in config["outbounds"]}
        self.assertEqual(outbounds["managed-residential-dns"]["settings"]["network"], "tcp")
        self.assertEqual(outbounds["managed-residential-dns"]["proxySettings"], {"tag": "residential"})
        self.assertEqual(config["dns"]["servers"], ["tcp://1.1.1.1", "tcp://8.8.8.8"])
        self.assertEqual(config["dns"]["hosts"], {"example.test": "192.0.2.1"})
        rules = config["routing"]["rules"]
        self.assertEqual(rules[0]["inboundTag"], ["managed-residential-dns-query"])
        self.assertEqual(rules[1]["inboundTag"], ["api"])
        self.assertEqual(rules[2]["port"], "53")
        self.assertEqual(rules[3]["outboundTag"], "managed-residential-udp-block")
        self.assertEqual(rules[4]["network"], "tcp")
        self.assertEqual(rules[5]["outboundTag"], "direct")

    def test_proxy_mode_keeps_full_udp_without_dns_rewrite(self):
        config = self.udp_config("proxy")
        apply_managed_outbounds(config)
        self.assertEqual(config["routing"]["rules"][1]["network"], "tcp,udp")
        self.assertEqual(config["dns"], {"hosts": {"example.test": "192.0.2.1"}})
        self.assertEqual(len(config["outbounds"]), 2)

    def test_compatibility_tags_and_invalid_modes_rejected(self):
        for mode, protocol in (("invalid", "socks"), ("proxy", "http"), ([], "socks"), ({}, "socks")):
            with self.assertRaises(OutboundConfigError):
                apply_managed_outbounds(self.udp_config(mode, protocol))
        for tag in ("managed-residential-dns", "managed-residential-dns-query", "managed-residential-udp-block"):
            config = self.udp_config()
            config["outbounds"].append({"tag": tag, "protocol": "freedom"})
            with self.assertRaisesRegex(OutboundConfigError, "reserved"):
                apply_managed_outbounds(config)

    def test_invalid_policy_does_not_partially_mutate_config(self):
        config = self.udp_config()
        config["outbounds"].append({"tag": "managed-residential-dns", "protocol": "freedom"})
        original = deepcopy(config)
        with self.assertRaises(OutboundConfigError):
            apply_managed_outbounds(config)
        self.assertEqual(config, original)

    def test_tcp_only_preserves_explicit_route_priority(self):
        config = self.udp_config()
        config["routing"]["rules"].insert(1, {"type": "field", "ip": ["192.0.2.0/24"], "outboundTag": "direct"})
        apply_managed_outbounds(config)
        rules = config["routing"]["rules"]
        self.assertEqual(rules[2]["ip"], ["192.0.2.0/24"])
        self.assertEqual(rules[3]["outboundTag"], "managed-residential-dns")

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
            for mode, authenticated in (("legacy", False), ("legacy", True), ("tcp_only", False), ("tcp_only", True)):
                with self.subTest(protocol=protocol, mode=mode, authenticated=authenticated):
                    profile = {"tag": "residential", "protocol": protocol,
                               "server": "proxy.example.net", "port": 8080, "udp_mode": mode}
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
