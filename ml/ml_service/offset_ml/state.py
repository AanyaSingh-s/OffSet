"""Per-user behavioural state. Identical code runs in batch training and online inference."""
from __future__ import annotations

import math
from bisect import bisect_left, insort
from collections import Counter

from .events import TxEvent

HORIZON_S = 72 * 3600  # events older than this (relative to the newest) are dropped from window lists


def local_time_parts(ts: float, tz_offset_s: int) -> tuple[float, int, bool]:
    """Return (fractional hour of day, day index, is_weekend) in the configured timezone."""
    local = ts + tz_offset_s
    day = math.floor(local / 86400)
    hour = (local - day * 86400) / 3600.0
    weekday = (day + 3) % 7  # 1970-01-01 was a Thursday (Mon=0)
    return hour, day, weekday >= 5


class UserState:
    def __init__(self, tz_offset_s: int = 19800):
        self.tz = tz_offset_s
        self.signed: list[float] = []
        self.rows: list[tuple[float, float, float, str]] = []  # signed_at, sync_at, amount, receiver
        self.n = 0
        self.log_mean = 0.0
        self.log_m2 = 0.0
        self.sorted_amounts: list[float] = []
        self.receivers: Counter = Counter()
        self.hour_counts = [0] * 24
        self.weekend_count = 0
        self.seen_hashes: dict[str, float] = {}
        self.seen_nonces: set[str] = set()
        self.devices: set[str] = set()
        self.last_seq: int | None = None
        self.last_local_post: float | None = None
        self.last_snapshot: int | None = None
        self.last_sync: float | None = None
        self.last_device: str | None = None

    def log_std(self) -> float:
        """Sample standard deviation (n-1 denominator) of ln(amount); 0 if fewer than two points."""
        return math.sqrt(self.log_m2 / (self.n - 1)) if self.n >= 2 else 0.0

    def median(self) -> float | None:
        k = len(self.sorted_amounts)
        if k == 0:
            return None
        mid = k // 2
        return self.sorted_amounts[mid] if k % 2 else 0.5 * (self.sorted_amounts[mid - 1] + self.sorted_amounts[mid])

    def mean_amount(self) -> float:
        return sum(self.sorted_amounts) / self.n if self.n else 0.0

    def _range(self, lo_ts: float, hi_ts: float) -> tuple[int, int]:
        return bisect_left(self.signed, lo_ts), bisect_left(self.signed, hi_ts)

    def window(self, s: float, seconds: float) -> tuple[int, float]:
        """Count and spend of settled events with signed_at in [s - seconds, s)."""
        lo, hi = self._range(s - seconds, s)
        return hi - lo, sum(r[2] for r in self.rows[lo:hi])

    def day_totals(self, s: float) -> tuple[int, float]:
        """Count and spend of settled events earlier on the same local calendar day as s."""
        _, day, _ = local_time_parts(s, self.tz)
        day_start = day * 86400 - self.tz
        lo, hi = self._range(day_start, s)
        return hi - lo, sum(r[2] for r in self.rows[lo:hi])

    def queue(self, s: float) -> tuple[int, float]:
        """Earlier events signed within 48 h that had not yet been synchronised when s was signed."""
        lo, hi = self._range(s - 48 * 3600, s)
        pending = [r for r in self.rows[lo:hi] if r[1] > s]
        return len(pending), sum(r[2] for r in pending)

    def seconds_since_previous(self, s: float) -> float | None:
        hi = bisect_left(self.signed, s)
        return s - self.signed[hi - 1] if hi > 0 else None

    def hour_share(self, hour: float, strength: float) -> float:
        """Smoothed share of past activity within +-2 h of this hour of day (5 of 24 hourly bins)."""
        h = int(hour) % 24
        k = sum(self.hour_counts[(h + d) % 24] for d in range(-2, 3))
        return (k + strength * 5 / 24) / (self.n + strength)

    def daytype_share(self, weekend: bool, strength: float) -> float:
        same = self.weekend_count if weekend else self.n - self.weekend_count
        prior = 2 / 7 if weekend else 5 / 7
        return (same + strength * prior) / (self.n + strength)

    def update(self, ev: TxEvent, settled: bool) -> None:
        """Record an event after it has been scored. Behavioural history only grows on settled events."""
        first_sight = ev.packet_hash not in self.seen_hashes
        if first_sight:
            self.seen_hashes[ev.packet_hash] = ev.sync_at
            self.seen_nonces.add(ev.nonce)
            d = ev.device
            if d is not None:
                self.devices.add(d.device_id)
                if self.last_seq is None or d.local_seq > self.last_seq:
                    self.last_seq = d.local_seq
                    self.last_local_post = d.local_pre_balance - ev.amount
                    self.last_snapshot = d.snapshot_version
                    self.last_sync = d.last_sync_at
                    self.last_device = d.device_id
        if not settled:
            return
        idx = bisect_left(self.signed, ev.signed_at)
        self.signed.insert(idx, ev.signed_at)
        self.rows.insert(idx, (ev.signed_at, ev.sync_at, ev.amount, ev.receiver_id))
        self.n += 1
        x = math.log(ev.amount)
        delta = x - self.log_mean
        self.log_mean += delta / self.n
        self.log_m2 += delta * (x - self.log_mean)
        insort(self.sorted_amounts, ev.amount)
        self.receivers[ev.receiver_id] += 1
        hour, _, weekend = local_time_parts(ev.signed_at, self.tz)
        self.hour_counts[int(hour) % 24] += 1
        self.weekend_count += int(weekend)
        cutoff = self.signed[-1] - HORIZON_S
        drop = bisect_left(self.signed, cutoff)
        if drop:
            del self.signed[:drop]
            del self.rows[:drop]


class StateStore:
    def __init__(self, tz_offset_s: int = 19800):
        self.tz = tz_offset_s
        self._states: dict[str, UserState] = {}

    def get(self, user_id: str) -> UserState:
        st = self._states.get(user_id)
        if st is None:
            st = self._states[user_id] = UserState(self.tz)
        return st

    def __len__(self) -> int:
        return len(self._states)
