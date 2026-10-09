import numpy as np
import pandas as pd

from OffSet.ml_service.offset_ml.data.generator import generate
from OffSet.ml_service.offset_ml.data.validate import check_dataset
from OffSet.ml_service.offset_ml.rules import evaluate
from OffSet.ml_service.offset_ml.pipeline import build_features


def test_all_dataset_checks_pass(small, cfg):
    raw, _, feats = small
    checks, summary = check_dataset(raw, feats, cfg)
    failed = [c for c in checks if not c[1]]
    assert not failed, failed
    assert summary["fraud_rows"] > 0


def test_generator_is_deterministic(cfg):
    c = type(cfg)(**{**cfg.__dict__})
    c.generator = type(cfg.generator)(**{**cfg.generator.__dict__, "n_users": 20})
    a, _ = generate(c)
    b, _ = generate(c)
    pd.testing.assert_frame_equal(a, b)


def test_all_scenarios_present_and_labelled(small):
    raw, _, _ = small
    fraud = raw[raw.fraud_label == 1]
    assert fraud.fraud_scenario.nunique() >= 8
    assert (raw[raw.fraud_label == 0].fraud_scenario == "").all()


def test_user_split_has_no_overlap(small):
    _, _, feats = small
    users_per_split = feats.groupby("split").user_id.apply(set)
    assert not (users_per_split["train"] & users_per_split["test"])
    assert not (users_per_split["train"] & users_per_split["val"])


def test_non_negative_balances_and_cold_start_rows(small):
    raw, _, feats = small
    assert (raw.server_balance_before >= 0).all()
    cold = feats[feats.is_cold_start == 1]
    assert len(cold) > 0 and (cold.amount_zscore == 0).all()
    assert np.isfinite(feats.select_dtypes("number").to_numpy()).all()
