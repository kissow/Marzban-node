"""Collect lightweight, read-only runtime metrics for a Marzban Node."""

import shutil
import threading
import time
from datetime import datetime, timezone


_CACHE_SECONDS = 5
_lock = threading.Lock()
_cached_at = 0.0
_cached_snapshot = None
_cpu_sample = None


def _read_text(path):
    try:
        with open(path, "r", encoding="ascii") as file:
            return file.read().strip()
    except (OSError, UnicodeError):
        return None


def _cpu_percent():
    global _cpu_sample
    content = _read_text("/proc/stat")
    if not content:
        return None
    fields = content.splitlines()[0].split()
    if not fields or fields[0] != "cpu":
        return None
    try:
        values = [int(value) for value in fields[1:]]
    except ValueError:
        return None
    if len(values) < 4:
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    previous = _cpu_sample
    _cpu_sample = (total, idle)
    if previous is None:
        return None
    total_delta = total - previous[0]
    idle_delta = idle - previous[1]
    if total_delta <= 0 or idle_delta < 0 or idle_delta > total_delta:
        return None
    return round((total_delta - idle_delta) * 100.0 / total_delta, 2)


def _memory_bytes():
    # Prefer the container's cgroup limit when available; otherwise report
    # the operating-system memory visible to the Node process.
    for limit_path, usage_path in (
        ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current"),
        ("/sys/fs/cgroup/memory/memory.limit_in_bytes",
         "/sys/fs/cgroup/memory/memory.usage_in_bytes"),
    ):
        limit, usage = _read_text(limit_path), _read_text(usage_path)
        if limit and usage and limit != "max":
            try:
                total, used = int(limit), int(usage)
                if 0 < total < 1 << 60 and 0 <= used <= total:
                    return total, used, "node-cgroup"
            except ValueError:
                pass

    content = _read_text("/proc/meminfo")
    if not content:
        return None, None, "node-os"
    values = {}
    for line in content.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].rstrip(":") in ("MemTotal", "MemAvailable"):
            try:
                values[parts[0].rstrip(":")] = int(parts[1]) * 1024
            except ValueError:
                continue
    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    if total is None or available is None or available > total:
        return None, None, "node-os"
    return total, total - available, "node-os"


def snapshot():
    """Return a cached metric sample without exposing host/user data."""
    global _cached_at, _cached_snapshot
    with _lock:
        now = time.monotonic()
        if _cached_snapshot is not None and now - _cached_at < _CACHE_SECONDS:
            return dict(_cached_snapshot)

        memory_total, memory_used, memory_scope = _memory_bytes()
        try:
            disk = shutil.disk_usage("/")
            disk_total, disk_used = disk.total, disk.used
        except OSError:
            disk_total, disk_used = None, None

        uptime_text = _read_text("/proc/uptime")
        try:
            uptime = int(float(uptime_text.split()[0])) if uptime_text else None
        except (ValueError, IndexError):
            uptime = None

        _cached_snapshot = {
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "source": "node-runtime",
            "capabilities": [
                "managed-outbounds-v1",
                "managed-outbounds-udp-v1",
                "device-policy-v1",
                "xray-user-stats-v1",
            ],
            "cpu_percent": _cpu_percent(),
            "memory_total_bytes": memory_total,
            "memory_used_bytes": memory_used,
            "disk_total_bytes": disk_total,
            "disk_used_bytes": disk_used,
            "uptime_seconds": uptime,
            # Live activity and policy metadata are merged by the service,
            # outside this resource cache, to avoid stale sync acknowledgements.
            "active_users": None,
            "disk_path": "/",
            "cpu_scope": "node-os",
            "memory_scope": memory_scope,
            "disk_scope": "node-root-filesystem",
            "uptime_scope": "node-kernel",
        }
        _cached_at = now
        return dict(_cached_snapshot)
