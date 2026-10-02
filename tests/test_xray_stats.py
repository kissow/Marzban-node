import unittest
from unittest.mock import Mock, patch

import grpc
import xray_stats as stats


def field(number, payload):
    return stats._encode_varint((number << 3) | 2) + stats._encode_varint(len(payload)) + payload


class XrayStatsTests(unittest.TestCase):
    def test_protobuf_decoder_reads_counters_and_ignores_unknown_fields(self):
        stat = field(1, b"user>>>1.alice>>>traffic>>>uplink") + b"\x10" + stats._encode_varint(500)
        payload = field(1, stat) + field(5, b"extra")
        self.assertEqual(stats.decode_query_response(payload), [("user>>>1.alice>>>traffic>>>uplink", 500)])
        self.assertEqual(stats.decode_online_users(field(1, b"alice") * 2 + field(1, b"bob")), {"alice", "bob"})

    def test_truncated_or_invalid_wire_data_is_rejected(self):
        for payload in (b"\x0a\x05x", b"\x09xx", b"\x0dxx", b"\x00", b"\x80" * 10):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                stats.decode_query_response(payload)

    def test_rpc_query_never_resets_billing_counters(self):
        client, channel = stats.XrayStatsClient(), Mock()
        stat = field(1, b"user>>>1.alice>>>traffic>>>downlink") + b"\x10\x07"
        channel.unary_unary.return_value.return_value = field(1, stat)
        with patch.object(client, "_channel", return_value=channel):
            self.assertEqual(client.user_totals(), {"1.alice": {"uplink": 0, "downlink": 7}})
        channel.unary_unary.return_value.assert_called_once_with(b"\x0a\x07user>>>\x10\x00", timeout=2)
        channel.close.assert_called_once()

    def test_only_unimplemented_core_falls_back_and_channel_is_closed(self):
        client, channel = stats.XrayStatsClient(), Mock()
        error = grpc.RpcError()
        error.code = lambda: grpc.StatusCode.UNIMPLEMENTED
        channel.unary_unary.return_value.side_effect = error
        with patch.object(client, "_channel", return_value=channel):
            self.assertIsNone(client.online_users())
            error.code = lambda: grpc.StatusCode.UNAVAILABLE
            with self.assertRaises(grpc.RpcError):
                client.online_users()
        self.assertEqual(channel.close.call_count, 2)
