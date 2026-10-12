"""Deterministic security layer.

NATIVE rules mirror checks that exist in the Java backend (idempotency, freshness, balance).
POLICY rules are proposed additions (limits, nonce store, device-state consistency) and need the
optional device fields in the payment payload.
"""
from __future__ import annotations

from .config import PolicyConfig
from .events import TxEvent
from .state import UserState

NATIVE_RULES = ("N_DUPLICATE_PACKET", "N_STALE", "N_FUTURE_DATED", "N_INSUFFICIENT_BALANCE")
POLICY_RULES = ("X_TX_LIMIT", "X_DAILY_LIMIT", "X_VELOCITY", "X_OFFLINE_DURATION", "X_NONCE_REUSE",
                "X_SEQUENCE", "X_BALANCE_CHAIN", "X_SNAPSHOT_REGRESSION")
ALL_RULES = NATIVE_RULES + POLICY_RULES


def native_flags(ev: TxEvent, first_seen_sync: float | None, p: PolicyConfig) -> dict[str, bool]:
    lag = ev.sync_at - ev.signed_at
    return {
        "N_DUPLICATE_PACKET": first_seen_sync is not None and ev.sync_at - first_seen_sync <= p.idempotency_ttl_s,
        "N_STALE": lag > p.packet_max_age_s,
        "N_FUTURE_DATED": lag < -p.future_skew_s,
        "N_INSUFFICIENT_BALANCE": ev.amount > ev.server_balance + p.balance_tol,
    }


def evaluate(ev: TxEvent, st: UserState, p: PolicyConfig) -> dict[str, bool]:
    """Evaluate every rule against the pre-event state. Policy rules needing device data are False without it."""
    flags = native_flags(ev, st.seen_hashes.get(ev.packet_hash), p)
    s = ev.signed_at
    cnt_1h, _ = st.window(s, 3600)
    _, day_spend = st.day_totals(s)
    flags["X_TX_LIMIT"] = ev.amount > p.max_amount
    flags["X_DAILY_LIMIT"] = day_spend + ev.amount > p.daily_limit
    flags["X_VELOCITY"] = cnt_1h + 1 > p.max_tx_per_hour
    d = ev.device
    flags["X_NONCE_REUSE"] = d is not None and ev.nonce in st.seen_nonces
    flags["X_OFFLINE_DURATION"] = d is not None and (s - d.last_sync_at) > p.max_offline_hours * 3600
    flags["X_SEQUENCE"] = d is not None and st.last_seq is not None and d.local_seq <= st.last_seq
    flags["X_BALANCE_CHAIN"] = (
        d is not None and st.last_local_post is not None and d.last_sync_at == st.last_sync
        and abs(d.local_pre_balance - st.last_local_post) > p.balance_tol)
    flags["X_SNAPSHOT_REGRESSION"] = (
        d is not None and st.last_snapshot is not None and d.snapshot_version < st.last_snapshot)
    return flags


def native_reject(flags: dict[str, bool]) -> bool:
    return any(flags[r] for r in NATIVE_RULES)


def policy_reject(flags: dict[str, bool]) -> bool:
    return any(flags[r] for r in ALL_RULES)


def fired(flags: dict[str, bool]) -> list[str]:
    return [r for r in ALL_RULES if flags.get(r)]
