"""Node-scoped online-user sample with a best-effort traffic fallback."""

import threading
import time
from datetime import datetime, timezone


class DeviceActivityTracker:
    def __init__(self, totals_reader, window_seconds=120, cache_seconds=5,
                 online_reader=None):
        self._totals_reader = totals_reader
        self._online_reader = online_reader
        self.window_seconds = max(30, int(window_seconds))
        self.cache_seconds = max(1, int(cache_seconds))
        self._lock = threading.Lock()
        self._baseline = None
        self._baseline_at = None
        self._active_at = {}
        self._last = None
        self._last_at = 0.0

    def reset(self):
        """Clear samples after a successful core start/stop/restart."""
        with self._lock:
            self._baseline = self._baseline_at = self._last = None
            self._active_at.clear()
            self._last_at = 0.0

    def snapshot(self):
        with self._lock:
            now = time.monotonic()
            if self._last is not None and now - self._last_at < self.cache_seconds:
                return dict(self._last)
            source, scope = "xray-user-stats-delta", "recent_traffic"
            window, sampled_at = self.window_seconds, None
            reason, active_users = None, None
            try:
                online = self._online_reader() if self._online_reader else None
                if online is not None:
                    active_users = len(set(online))
                    source, scope, window = "xray-online-users", "online_users", None
                else:
                    totals = self._totals_reader()
                    if not isinstance(totals, dict):
                        raise ValueError("invalid traffic stats")
                    totals = {
                        user: {link: values.get(link, 0) for link in ("uplink", "downlink")}
                        for user, values in totals.items()
                    }
                    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0
                           for values in totals.values() for v in values.values()):
                        raise ValueError("invalid traffic counter")
                    if self._baseline is None or now - self._baseline_at > self.window_seconds:
                        self._active_at.clear()
                        reason = "sampling_baseline"
                    else:
                        for user, current in totals.items():
                            previous = self._baseline.get(user)
                            # The panel resets counters while billing traffic.
                            # A positive reset value is observed traffic; one
                            # reset must not erase other users' activity.
                            if previous is None:
                                grew = any(current.values())
                            else:
                                grew = any(current[link] > previous[link] or
                                           (current[link] < previous[link] and current[link] > 0)
                                           for link in current)
                            if grew:
                                self._active_at[user] = now
                        self._active_at = {u: ts for u, ts in self._active_at.items()
                                           if u in totals and now - ts < self.window_seconds}
                        active_users = len(self._active_at)
                    self._baseline, self._baseline_at = totals, now
                sampled_at = datetime.now(timezone.utc).isoformat()
            except Exception:
                reason = "stats_unavailable"
            self._last = {
                "active_users": active_users,
                "active_users_window_seconds": window,
                "active_users_sampled_at": sampled_at,
                "activity_source": source,
                "activity_scope": scope,
                "activity_reason": reason,
            }
            self._last_at = now
            return dict(self._last)
