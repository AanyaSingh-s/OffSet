"""Batch feature pipeline: replays each user's events chronologically through the same state code the API uses."""
from __future__ import annotations

import pandas as pd

from . import rules
from .config import Config
from .events import DeviceInfo, TxEvent
from .features import EXTENDED_FEATURES, compute_features
from .logging_utils import get_logger
from .state import UserState

log = get_logger("pipeline")

META_COLUMNS = ["tx_id", "user_id", "receiver_id", "amount", "signed_at", "sync_at", "outcome",
                "fraud_label", "fraud_scenario", "fraud_variant", "attack_id", "archetype"]


def row_to_event(r) -> TxEvent:
    dev = DeviceInfo(r.device_id, int(r.local_seq), float(r.local_pre_balance),
                     int(r.snapshot_version), float(r.last_sync_at))
    return TxEvent(r.user_id, r.receiver_id, float(r.amount), float(r.signed_at), float(r.sync_at),
                   r.packet_hash, r.nonce, float(r.server_balance_before), int(r.server_version_before), dev)


def build_features(raw: pd.DataFrame, users: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Return one row per transaction: metadata, all features, rule flags and rule verdicts."""
    raw = raw.sort_values(["user_id", "arrival_idx"], kind="stable")
    records = []
    for user_id, group in raw.groupby("user_id", sort=False):
        st = UserState(cfg.generator.tz_offset_s)
        for r in group.itertuples(index=False):
            ev = row_to_event(r)
            flags = rules.evaluate(ev, st, cfg.policy)
            rec = {"tx_id": r.tx_id}
            rec.update(compute_features(ev, st, cfg.features))
            rec.update(flags)
            rec["rules_native_reject"] = rules.native_reject(flags)
            rec["rules_policy_reject"] = rules.policy_reject(flags)
            records.append(rec)
            st.update(ev, settled=not rules.native_reject(flags))
    feats = pd.DataFrame.from_records(records)
    meta = raw.merge(users[["user_id", "archetype"]], on="user_id")[META_COLUMNS]
    out = meta.merge(feats, on="tx_id", validate="one_to_one")
    for col in EXTENDED_FEATURES:
        out[col] = out[col].astype(float)
    log.info("built features for %d rows (%d features)", len(out), len(EXTENDED_FEATURES))
    return out
