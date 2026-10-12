import math

import numpy as np

from OffSet.ml_service.offset_ml.config import FeatureConfig
from OffSet.ml_service.offset_ml.events import DeviceInfo, TxEvent
from OffSet.ml_service.offset_ml.features import compute_features, slog
from OffSet.ml_service.offset_ml.state import UserState

FC = FeatureConfig()


def ev(amount, signed, sync=None, receiver="r1", h=None, bal=5000.0, dev=None):
    return TxEvent("u", receiver, amount, signed, sync if sync is not None else signed + 60,
                   h or f"h{signed}", f"n{signed}", bal, 0, dev)


def test_welford_matches_numpy():
    st = UserState()
    amounts = [50, 80, 120, 60, 200, 90]
    for i, a in enumerate(amounts):
        st.update(ev(a, 1000 + i * 100), True)
    logs = np.log(amounts)
    assert math.isclose(st.log_mean, logs.mean())
    assert math.isclose(st.log_std(), logs.std(ddof=1))
    assert st.median() == np.median(amounts)


def test_zscore_formula_and_cold_start():
    st = UserState()
    base = 10_000_000
    for i, a in enumerate([50, 60, 70, 55]):
        st.update(ev(a, base + i * 7200), True)
    assert compute_features(ev(500, base + 40000), st, FC)["amount_zscore"] == 0.0  # 4 < min_history
    st.update(ev(65, base + 30000), True)
    logs = np.log([50, 60, 70, 55, 65])
    expected = (math.log(500) - logs.mean()) / max(logs.std(ddof=1), FC.std_floor)
    assert math.isclose(compute_features(ev(500, base + 40000), st, FC)["amount_zscore"], min(expected, FC.z_clip))


def test_windows_are_strictly_prior():
    st = UserState()
    t = 5_000_000
    for dt in (-3000, -500, -100):
        st.update(ev(100, t + dt), True)
    f = compute_features(ev(100, t), st, FC)
    assert (f["cnt_10m"], f["cnt_1h"], f["cnt_24h"]) == (2, 3, 3)
    st.update(ev(100, t + 50), True)  # later event must not change the earlier event's features
    assert compute_features(ev(100, t), st, FC)["cnt_10m"] == 2


def test_no_future_leakage_prefix_equals_full(small):
    from OffSet.ml_service.offset_ml.pipeline import build_features
    raw, users, feats = small
    uid = raw.groupby("user_id").size().idxmax()
    sub = raw[raw.user_id == uid]
    cfg_ = __import__("offset_ml.config", fromlist=["load_config"]).load_config()
    half = sub.iloc[: len(sub) // 2]
    f_half = build_features(half, users, cfg_).set_index("tx_id")
    f_full = feats.set_index("tx_id").loc[f_half.index]
    cols = ["amount_zscore", "cnt_1h", "queue_depth", "hist_n" if "hist_n" in f_full else "log_hist_n", "chain_gap"]
    np.testing.assert_allclose(f_half[cols].to_numpy(), f_full[cols].to_numpy())


def test_queue_depth_counts_unsynced_prior_events():
    st = UserState()
    st.update(ev(100, 1000, sync=9000), True)
    st.update(ev(100, 1100, sync=9001), True)
    st.update(ev(100, 2000, sync=2100), True)  # synced before the next tx is signed
    f = compute_features(ev(100, 3000, sync=9002), st, FC)
    assert f["queue_depth"] == 3 and math.isclose(f["log_queue_spend"], math.log1p(300))


def test_hour_share_and_daytype_bounded():
    st = UserState()
    for i in range(10):
        st.update(ev(100, 1_700_000_000 + i * 86400), True)
    f = compute_features(ev(100, 1_700_000_000 + 11 * 86400), st, FC)
    assert 0 < f["hour_share"] <= 1 and 0 < f["daytype_share"] <= 1


def test_device_features():
    st = UserState()
    d0 = DeviceInfo("d0", 1, 1000.0, 3, 900.0)
    st.update(ev(100, 1000, dev=d0), True)
    d1 = DeviceInfo("d1", 2, 900.0, 3, 900.0)
    f = compute_features(ev(100, 1200, dev=d1, bal=900.0), st, FC)
    assert f["device_new"] == 1.0 and f["device_changed"] == 1.0 and f["chain_gap"] == 0.0 and f["seq_gap"] == 0.0
    bad = DeviceInfo("d0", 2, 1500.0, 3, 900.0)
    f = compute_features(ev(100, 1200, dev=bad, bal=900.0), st, FC)
    assert math.isclose(f["chain_gap"], slog(600.0))


def test_slog_symmetry():
    assert slog(0) == 0 and math.isclose(slog(-5), -slog(5))
