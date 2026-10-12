import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier

from OffSet.ml_service.offset_ml.features import TIERS
from OffSet.ml_service.offset_ml.pipeline import row_to_event
from OffSet.ml_service.offset_ml.service.app import create_app
from OffSet.ml_service.offset_ml.service.scoring import Scorer
from OffSet.ml_service.offset_ml.state import StateStore
from OffSet.ml_service.offset_ml.features import compute_features
from OffSet.ml_service.offset_ml import rules


@pytest.fixture(scope="module")
def scorer(small, cfg):
    _, _, feats = small
    bundles = {}
    for tier, cols in TIERS.items():
        train = feats[feats.split == "train"]
        rf = RandomForestClassifier(n_estimators=20, random_state=0).fit(train[cols], train.fraud_label)
        meta = {"tier": tier, "model_name": "random_forest", "features": cols, "model_version": f"test-{tier}",
                "thresholds": {"medium": 0.3, "high": 0.7}}
        bundles[tier] = (rf, meta)
    return Scorer(bundles, cfg)


def test_online_features_match_batch_features(small, cfg):
    raw, _, feats = small
    uid = raw.groupby("user_id").size().idxmax()
    store, expected = StateStore(cfg.generator.tz_offset_s), feats.set_index("tx_id")
    for r in raw[raw.user_id == uid].sort_values("arrival_idx").itertuples(index=False):
        ev = row_to_event(r)
        st = store.get(uid)
        got = compute_features(ev, st, cfg.features)
        flags = rules.evaluate(ev, st, cfg.policy)
        row = expected.loc[r.tx_id]
        for k, v in got.items():
            assert np.isclose(v, row[k]), (r.tx_id, k, v, row[k])
        st.update(ev, settled=not rules.native_reject(flags))


def payload(**over):
    base = {"sender_vpa": "alice@demo", "receiver_vpa": "bob@demo", "amount": 100.0, "signed_at_ms": 1_700_000_000_000,
            "settled_at_ms": 1_700_000_060_000, "server_balance": 5000.0, "server_version": 2,
            "packet_hash": "abc", "nonce": "n-1"}
    base.update(over)
    return base


def test_endpoints(scorer, cfg):
    with TestClient(create_app(scorer, cfg)) as client:
        assert client.get("/health").json() == {"status": "ok", "model_loaded": True}
        assert "extended" in client.get("/v1/model").json()
        r = client.post("/v1/assess", json=payload())
        body = r.json()
        assert r.status_code == 200 and 0 <= body["risk_score"] <= 1
        assert body["risk_level"] in {"LOW", "MEDIUM", "HIGH"} and body["feature_tier"] == "native"
        dev = {"device_id": "d1", "local_seq": 1, "local_pre_balance": 5000.0, "snapshot_version": 2,
               "last_sync_at_ms": 1_699_999_000_000}
        r2 = client.post("/v1/assess", json=payload(packet_hash="def", nonce="n-2", device=dev))
        assert r2.json()["feature_tier"] == "extended"


def test_rejects_invalid_payload_and_policy_violation(scorer, cfg):
    with TestClient(create_app(scorer, cfg)) as client:
        assert client.post("/v1/assess", json=payload(amount=-5)).status_code == 422
        r = client.post("/v1/assess", json=payload(packet_hash="zzz", nonce="n-9", amount=9000, server_balance=100))
        assert r.json()["action"] == "REJECT" and "N_INSUFFICIENT_BALANCE" in r.json()["policy_violations"]


def test_service_without_models_is_degraded(tmp_path, monkeypatch, cfg):
    monkeypatch.setenv("OFFSET_ML_MODEL_DIR", str(tmp_path))
    with TestClient(create_app(cfg=cfg)) as client:
        assert client.get("/health").json()["status"] == "degraded"
        assert client.post("/v1/assess", json=payload()).status_code == 503


def test_threshold_override(scorer, cfg):
    s = Scorer(scorer.bundles, cfg, medium=0.0, high=0.0)
    with TestClient(create_app(s, cfg)) as client:
        assert client.post("/v1/assess", json=payload(packet_hash="q", nonce="q")).json()["risk_level"] == "HIGH"
