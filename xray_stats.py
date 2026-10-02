"""Small Xray StatsService client used by the Node activity sampler.

The Node intentionally keeps this client independent from the panel package.  The
wire format is the stable protobuf contract used by Xray's StatsService; keeping
the encoder/decoder here avoids copying the panel's generated Python package.
"""

import grpc

from config import XRAY_API_HOST, XRAY_API_PORT, SSL_CERT_FILE


def _encode_varint(value: int) -> bytes:
    output = bytearray()
    value = int(value)
    if value < 0:
        raise ValueError("varint must be nonnegative")
    while value > 0x7F:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value & 0x7F)
    return bytes(output)


def _read_varint(data: bytes, offset: int):
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if shift == 63 and byte > 1:
            raise ValueError("invalid protobuf varint")
        if not byte & 0x80:
            return value, offset
        shift += 7
        if shift > 63:
            raise ValueError("invalid protobuf varint")
    raise ValueError("truncated protobuf varint")


def _read_field(data: bytes, offset: int):
    key, offset = _read_varint(data, offset)
    field_number, wire_type = key >> 3, key & 0x07
    if field_number == 0:
        raise ValueError("invalid protobuf field")
    if wire_type == 0:
        value, offset = _read_varint(data, offset)
    elif wire_type == 2:
        length, offset = _read_varint(data, offset)
        end = offset + length
        if end > len(data):
            raise ValueError("truncated protobuf field")
        value, offset = data[offset:end], end
    elif wire_type == 1:
        end = offset + 8
        if end > len(data):
            raise ValueError("truncated protobuf field")
        value, offset = data[offset:end], end
    elif wire_type == 5:
        end = offset + 4
        if end > len(data):
            raise ValueError("truncated protobuf field")
        value, offset = data[offset:end], end
    else:
        raise ValueError("unsupported protobuf wire type")
    return field_number, wire_type, value, offset


def _query_request(pattern: str) -> bytes:
    encoded = pattern.encode("utf-8")
    return b"\x0a" + _encode_varint(len(encoded)) + encoded + b"\x10\x00"


def _decode_stat(payload: bytes):
    name = None
    value = 0
    offset = 0
    while offset < len(payload):
        field, wire, raw, offset = _read_field(payload, offset)
        if field == 1 and wire == 2:
            name = raw.decode("utf-8", errors="replace")
        elif field == 2 and wire == 0:
            value = raw if raw < (1 << 63) else raw - (1 << 64)
    return name, value


def decode_query_response(payload: bytes):
    """Decode QueryStatsResponse into ``[(name, value), ...]``."""
    stats = []
    offset = 0
    while offset < len(payload):
        field, wire, raw, offset = _read_field(payload, offset)
        if field == 1 and wire == 2:
            name, value = _decode_stat(raw)
            if name:
                stats.append((name, value))
    return stats


def decode_online_users(payload: bytes):
    users = set()
    offset = 0
    while offset < len(payload):
        field, wire, raw, offset = _read_field(payload, offset)
        if field == 1 and wire == 2:
            users.add(raw.decode("utf-8"))
    return users


class XrayStatsClient:
    def __init__(self, host=None, port=None, certificate_path=None):
        self.host = host or XRAY_API_HOST
        if self.host in ("0.0.0.0", "::"):
            self.host = "127.0.0.1" if self.host == "0.0.0.0" else "::1"
        self.port = port or XRAY_API_PORT
        self.certificate_path = certificate_path or SSL_CERT_FILE

    def _channel(self):
        with open(self.certificate_path, "rb") as certificate:
            credentials = grpc.ssl_channel_credentials(certificate.read())
        return grpc.secure_channel(
            f"[{self.host}]:{self.port}" if ":" in self.host else f"{self.host}:{self.port}",
            credentials,
            options=(("grpc.ssl_target_name_override", "Gozargah"),),
        )

    def online_users(self, timeout=2):
        """Read users with entries in the core's online IP map.

        This counts users, never physical devices or TCP sockets.
        Unsupported older cores return None; connection errors propagate.
        """
        channel = self._channel()
        try:
            call = channel.unary_unary(
                "/xray.app.stats.command.StatsService/GetAllOnlineUsers",
                request_serializer=lambda value: value,
                response_deserializer=lambda value: value,
            )
            return decode_online_users(call(b"", timeout=timeout))
        except grpc.RpcError as exc:
            if exc.code() == grpc.StatusCode.UNIMPLEMENTED:
                return None
            raise
        finally:
            channel.close()

    def user_totals(self, timeout=2):
        """Return cumulative user traffic keyed by the Xray user identity."""
        channel = self._channel()
        try:
            call = channel.unary_unary(
                "/xray.app.stats.command.StatsService/QueryStats",
                request_serializer=lambda value: value,
                response_deserializer=lambda value: value,
            )
            payload = call(_query_request("user>>>"), timeout=timeout)
        finally:
            channel.close()

        totals = {}
        for name, value in decode_query_response(payload):
            parts = name.split(">>>")
            if len(parts) != 4 or parts[0] != "user" or parts[2] != "traffic" or not parts[1]:
                continue
            user, link = parts[1], parts[-1]
            if link not in ("uplink", "downlink"):
                continue
            totals.setdefault(user, {"uplink": 0, "downlink": 0})[link] = max(0, int(value))
        return totals
