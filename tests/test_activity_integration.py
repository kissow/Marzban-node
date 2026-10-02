"""Exercise the real fixed core, TLS Stats RPC and a local VLESS user."""

import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import grpc

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from xray import XRayConfig
from xray_stats import XrayStatsClient


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@unittest.skipUnless(os.environ.get("XRAY_TEST_BINARY"), "XRAY_TEST_BINARY is not configured")
class NodeActivityIntegrationTests(unittest.TestCase):
    def test_online_user_lifecycle_and_nonresetting_traffic_query(self):
        with tempfile.TemporaryDirectory(prefix="node-activity-test-") as directory:
            directory = Path(directory)
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Gozargah")])
            now = datetime.now(timezone.utc)
            certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                           .public_key(private_key.public_key()).serial_number(x509.random_serial_number())
                           .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
                           .add_extension(x509.SubjectAlternativeName([x509.DNSName("Gozargah")]), critical=False)
                           .sign(private_key, hashes.SHA256()))
            cert, key = directory / "cert.pem", directory / "key.pem"
            cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
            key.write_bytes(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                                      serialization.NoEncryption()))
            inbound_port, api_port = free_port(), free_port()
            account = uuid.uuid4()
            original = {"inbounds": [{"tag": "test", "listen": "127.0.0.1", "port": inbound_port,
                                       "protocol": "vless", "settings": {"decryption": "none", "clients": [
                                           {"id": str(account), "email": "1.alice", "level": 0}]}}],
                        "policy": {"levels": {"0": {"statsUserUplink": True, "statsUserDownlink": True}}},
                        "outbounds": [{"protocol": "freedom", "tag": "direct"}]}
            with patch.multiple("xray", XRAY_API_HOST="127.0.0.1", XRAY_API_PORT=api_port,
                                SSL_CERT_FILE=str(cert), SSL_KEY_FILE=str(key)):
                config = XRayConfig(json.dumps(original), "127.0.0.1")
            self.assertTrue(config["policy"]["levels"]["0"]["statsUserOnline"])
            self.assertTrue(config["policy"]["levels"]["0"]["statsUserUplink"])
            config_file = directory / "config.json"
            config_file.write_text(config.to_json(), encoding="utf-8")
            process = subprocess.Popen([os.environ["XRAY_TEST_BINARY"], "run", "-config", str(config_file)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                stats = XrayStatsClient(host="127.0.0.1", port=api_port, certificate_path=str(cert))
                deadline = time.monotonic() + 5
                while True:
                    try:
                        self.assertEqual(stats.online_users(timeout=0.2), set())
                        break
                    except grpc.RpcError:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            raise
                        time.sleep(0.1)
                with socket.socket() as echo_server:
                    echo_server.bind(("127.0.0.1", 0))
                    echo_server.listen()
                    echo_server.settimeout(3)
                    finish = threading.Event()
                    errors = []

                    def echo():
                        try:
                            with echo_server.accept()[0] as stream:
                                stream.settimeout(3)
                                stream.sendall(stream.recv(128))
                                finish.wait(5)
                        except Exception as exc:
                            errors.append(exc)

                    thread = threading.Thread(target=echo, daemon=True)
                    thread.start()
                    try:
                        with socket.create_connection(("127.0.0.1", inbound_port), timeout=3,
                                                      source_address=("127.0.0.2", 0)) as client:
                            client.settimeout(3)
                            request = (b"\x00" + account.bytes + b"\x00\x01" +
                                       echo_server.getsockname()[1].to_bytes(2, "big") +
                                       b"\x01" + socket.inet_aton("127.0.0.1") + b"hello")
                            client.sendall(request)
                            response = b""
                            while len(response) < 7:
                                packet = client.recv(128)
                                if not packet:
                                    break
                                response += packet
                            self.assertEqual(response, b"\x00\x00hello")
                            self.assertEqual(len(stats.online_users()), 1)
                            first = stats.user_totals()
                            second = stats.user_totals()
                            self.assertGreater(first["1.alice"]["uplink"], 0)
                            self.assertEqual(first, second)
                    finally:
                        finish.set()
                        thread.join(3)
                    self.assertEqual(errors, [])
                    deadline = time.monotonic() + 3
                    while stats.online_users() and time.monotonic() < deadline:
                        time.sleep(0.1)
                    self.assertEqual(stats.online_users(), set())
            finally:
                process.terminate()
                process.wait(timeout=5)
