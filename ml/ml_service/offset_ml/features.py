"""Causal feature engineering. Every value uses only the event itself and the user's prior state."""
from __future__ import annotations

import math

from .config import FeatureConfig
from .events import TxEvent
from .state import UserState, local_time_parts

NATIVE_FEATURES = [
    "log_amount", "amount_to_server_balance", "log_hist_n", "is_cold_start", "log_hist_median",
    "hist_std_log", "amount_over_median_log", "amount_zscore",
    "cnt_10m", "cnt_1h", "cnt_24h", "day_count", "log_day_spend", "log_spend_1h",
    "log_interval_s", "has_recent_prev",
    "receiver_prior_count", "receiver_share", "is_new_receiver", "n_receivers",
    "hour_sin", "hour_cos", "night_flag", "hour_share", "is_weekend", "daytype_share",
    "log_sync_lag_min", "queue_depth", "log_queue_spend",
]
DEVICE_FEATURES = [
    "chain_gap", "seq_gap", "local_server_gap", "snapshot_regress", "snapshot_staleness",
    "log_offline_min", "device_new", "device_changed",
]
EXTENDED_FEATURES = NATIVE_FEATURES + DEVICE_FEATURES
TIERS = {"native": NATIVE_FEATURES, "extended": EXTENDED_FEATURES}


def slog(x: float) -> float:
    """Signed log: sign(x) * ln(1 + |x|)."""
    return math.copysign(math.log1p(abs(x)), x)


def compute_features(ev: TxEvent, st: UserState, cfg: FeatureConfig) -> dict[str, float]:
    a, s = ev.amount, ev.signed_at
    n = st.n
    cold = n < cfg.min_history
    median = st.median()
    std_log = st.log_std()
    ln_a = math.log(a)

    if cold:
        z = 0.0
    else:
        z = (ln_a - st.log_mean) / max(std_log, cfg.std_floor)
        z = max(-cfg.z_clip, min(cfg.z_clip, z))

    prior_recv = st.receivers[ev.receiver_id]
    hour, _, weekend = local_time_parts(s, st.tz)
    cnt_10m, _ = st.window(s, 600)
    cnt_1h, spend_1h = st.window(s, 3600)
    cnt_24h, _ = st.window(s, 86400)
    day_cnt, day_spend = st.day_totals(s)
    q_cnt, q_spend = st.queue(s)
    gap_prev = st.seconds_since_previous(s)
    lag_min = (ev.sync_at - s) / 60.0

    f = {
        "log_amount": ln_a,
        "amount_to_server_balance": a / max(ev.server_balance, 1.0),
        "log_hist_n": math.log1p(n),
        "is_cold_start": float(cold),
        "log_hist_median": math.log(median) if median else ln_a,
        "hist_std_log": std_log,
        "amount_over_median_log": math.log(a / median) if median else 0.0,
        "amount_zscore": z,
        "cnt_10m": cnt_10m, "cnt_1h": cnt_1h, "cnt_24h": cnt_24h,
        "day_count": day_cnt + 1,
        "log_day_spend": math.log1p(day_spend + a),
        "log_spend_1h": math.log1p(spend_1h + a),
        "log_interval_s": math.log1p(gap_prev if gap_prev is not None else cfg.interval_cap_s),
        "has_recent_prev": float(gap_prev is not None),
        "receiver_prior_count": prior_recv,
        "receiver_share": prior_recv / n if n else 0.0,
        "is_new_receiver": float(n > 0 and prior_recv == 0),
        "n_receivers": len(st.receivers),
        "hour_sin": math.sin(2 * math.pi * hour / 24), "hour_cos": math.cos(2 * math.pi * hour / 24),
        "night_flag": float(hour < 5),
        "hour_share": st.hour_share(hour, cfg.prior_strength),
        "is_weekend": float(weekend),
        "daytype_share": st.daytype_share(weekend, cfg.prior_strength),
        "log_sync_lag_min": slog(lag_min),
        "queue_depth": q_cnt + 1,
        "log_queue_spend": math.log1p(q_spend + a),
    }

    d = ev.device
    chain = d is not None and st.last_seq is not None
    f["chain_gap"] = slog(d.local_pre_balance - st.last_local_post) if (
        chain and d.last_sync_at == st.last_sync) else 0.0
    f["seq_gap"] = slog(d.local_seq - st.last_seq - 1) if chain else 0.0
    f["local_server_gap"] = slog(d.local_pre_balance - ev.server_balance) if d else 0.0
    f["snapshot_regress"] = float(chain and d.snapshot_version < st.last_snapshot)
    f["snapshot_staleness"] = float(max(-5, min(50, ev.server_version - d.snapshot_version))) if d else 0.0
    f["log_offline_min"] = math.log1p(max(0.0, (s - d.last_sync_at) / 60.0)) if d else 0.0
    f["device_new"] = float(d is not None and bool(st.devices) and d.device_id not in st.devices)
    f["device_changed"] = float(chain and d.device_id != st.last_device)
    return f
