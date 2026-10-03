"""Real pinned-core DNS compatibility against a local TCP-only SOCKS server.

No production endpoint, credentials or external DNS server is contacted.
"""
import json
import os
import socket
import struct
import subprocess
import threading
import time
import unittest

from outbound_profiles import apply_managed_outbounds


def receive(sock, length):
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise EOFError("connection ended")
        data += chunk
    return data


@unittest.skipUnless(os.environ.get("XRAY_TEST_BINARY"), "XRAY_TEST_BINARY is not configured")
class EgressDnsRuntimeTests(unittest.TestCase):
    def run_query(self, query_type, protocol="socks"):
        records = []
        errors = []
        stop = threading.Event()
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(0.2)

        def serve():
            while not stop.is_set():
                try:
                    conn, _ = listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                with conn:
                    try:
                        conn.settimeout(4)
                        if protocol == "http":
                            header = b""
                            while not header.endswith(b"\r\n\r\n"):
                                header += receive(conn, 1)
                                if len(header) > 8192:
                                    raise ValueError("HTTP header too large")
                            method, address, _ = header.split(b"\r\n", 1)[0].decode().split()
                            self.assertEqual(method, "CONNECT")
                            target, port = address.rsplit(":", 1)
                            port, command = int(port), 1
                            conn.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                        else:
                            greeting = receive(conn, 2)
                            receive(conn, greeting[1])
                            conn.sendall(b"\x05\x00")
                            version, command, _, kind = receive(conn, 4)
                            if kind == 1:
                                target = socket.inet_ntoa(receive(conn, 4))
                            elif kind == 3:
                                target = receive(conn, receive(conn, 1)[0]).decode()
                            else:
                                target = socket.inet_ntop(socket.AF_INET6, receive(conn, 16))
                            port = struct.unpack("!H", receive(conn, 2))[0]
                            if command == 1:
                                conn.sendall(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x00")
                        records.append((command, target, port))
                        if command != 1:
                            conn.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
                            continue
                        size = struct.unpack("!H", receive(conn, 2))[0]
                        query = receive(conn, size)
                        # Reply with an A answer, or a valid empty TXT answer.
                        answer = b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04\xc0\x00\x02\x2a" if query_type == 1 else b""
                        reply = query[:2] + b"\x81\x80\x00\x01" + struct.pack("!H", bool(answer)) + b"\x00\x00\x00\x00" + query[12:] + answer
                        conn.sendall(struct.pack("!H", len(reply)) + reply)
                    except Exception as exc:
                        errors.append(str(exc))

        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        incoming = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        incoming.bind(("127.0.0.1", 0))
        incoming.settimeout(0.3)
        port_probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        port_probe.bind(("127.0.0.1", 0))
        inbound_port = port_probe.getsockname()[1]
        port_probe.close()
        config = {"log": {"loglevel": "warning"},
                  "inbounds": [{"tag": "test", "listen": "127.0.0.1", "port": inbound_port,
                    "protocol": "dokodemo-door", "settings": {"address": "1.1.1.1", "port": 53, "network": "udp"}}],
                  "outbounds": [{"tag": "direct", "protocol": "freedom"}],
                  "marzban_node_extensions": {"outbounds": [{"tag": "residential", "protocol": protocol,
                    "server": "127.0.0.1", "port": listener.getsockname()[1], "udp_mode": "tcp_only"}],
                    "default_outbound_tag": "residential"}}
        apply_managed_outbounds(config)
        process = subprocess.Popen([os.environ["XRAY_TEST_BINARY"], "run", "-config", "stdin:"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        response = None
        try:
            process.stdin.write(json.dumps(config))
            process.stdin.close()
            process.stdin = None
            name = b"\x07example\x04test\x00"
            query = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00" + name + struct.pack("!HH", query_type, 1)
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline and process.poll() is None:
                incoming.sendto(query, ("127.0.0.1", inbound_port))
                try:
                    response, _ = incoming.recvfrom(4096)
                    break
                except (socket.timeout, ConnectionResetError):
                    pass
        finally:
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
            stop.set()
            listener.close()
            worker.join(timeout=5)
            incoming.close()
        self.assertIsNotNone(response, f"{stdout}\n{stderr}\n{errors}\n{records}")
        self.assertEqual(response[:2], b"\x12\x34")
        self.assertEqual(response[3] & 15, 0)
        self.assertTrue(records)
        self.assertTrue(all(command == 1 and port == 53 for command, _, port in records), records)
        if query_type == 1:
            self.assertIn(b"\xc0\x00\x02\x2a", response)

    def test_a_query_uses_residential_tcp_not_udp_associate(self):
        self.run_query(1)

    def test_txt_query_is_tcp_framed_through_residential_proxy(self):
        self.run_query(16)

    def test_http_a_query_uses_connect_tunnel(self):
        self.run_query(1, "http")

    def test_http_txt_query_uses_connect_tunnel(self):
        self.run_query(16, "http")


if __name__ == "__main__":
    unittest.main()
