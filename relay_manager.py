"""Mr.shaw authenticated fixed-destination relay snapshot, no arbitrary config."""
import atexit
import json
import threading

from config import SERVICE_PORT, XRAY_API_PORT, XRAY_ASSETS_PATH, XRAY_EXECUTABLE_PATH
from node_relay import RelayProcess, clean_address

CAPABILITY = "managed-node-relay-v1"


class RelayManager:
    def __init__(self, runtime=None):
        self.runtime = runtime or RelayProcess(XRAY_EXECUTABLE_PATH, XRAY_ASSETS_PATH)
        self.lock = threading.RLock()
        atexit.register(self.stop)

    def state(self):
        with self.lock:
            return {"capability": CAPABILITY, "running": self.runtime.running,
                    "profiles": self.runtime.snapshot(), "error": self.runtime.last_error}

    def status(self):
        with self.lock:
            return {**self.state(), "occupied_ports": sorted(self.runtime.occupied_ports() | {SERVICE_PORT, XRAY_API_PORT})}

    def replace(self, profiles):
        # RPyC transports JSON; REST transports native lists. Validate both here.
        if isinstance(profiles, str):
            try:
                profiles = json.loads(profiles)
            except (ValueError, TypeError) as exc:
                raise ValueError("Invalid relay snapshot JSON") from exc
        if type(profiles) is not list or len(profiles) > 512:
            raise ValueError("A relay snapshot must be a list of at most 512 destinations")
        with self.lock:
            normalized, ids, ports = [], set(), set()
            occupied = self.runtime.occupied_ports() | {SERVICE_PORT, XRAY_API_PORT}
            for item in profiles:
                if type(item) is not dict or set(item) != {"node_id", "listen_port", "target_address", "target_port"}:
                    raise ValueError("Unexpected relay fields; arbitrary Xray configuration is not accepted")
                node_id, port, target_port = item["node_id"], item["listen_port"], item["target_port"]
                if type(node_id) is not int or node_id <= 0 or node_id in ids:
                    raise ValueError("Invalid or duplicate target Node id")
                if type(port) is not int or not 1024 <= port <= 65535 or port in ports or port in occupied:
                    raise ValueError("Relay listener port is invalid, reserved or occupied")
                if type(target_port) is not int or not 1 <= target_port <= 65535:
                    raise ValueError("Invalid target business port")
                if not isinstance(item["target_address"], str):
                    raise ValueError("Invalid target address")
                normalized.append({**item, "target_address": clean_address(item["target_address"])})
                ids.add(node_id)
                ports.add(port)
            # Prevent a snapshot from pointing at any of its own relay listeners.
            if any(item["target_port"] in ports for item in normalized):
                raise ValueError("A relay cannot target a managed relay port")
            self.runtime.apply(normalized)
            return self.state()

    def stop(self):
        with self.lock:
            self.runtime.stop()
