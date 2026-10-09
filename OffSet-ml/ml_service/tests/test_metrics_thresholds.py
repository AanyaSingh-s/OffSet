import numpy as np

from OffSet.ml_service.offset_ml.metrics import binary_metrics, hybrid_score
from OffSet.ml_service.offset_ml.thresholds import best_threshold, high_threshold


def test_binary_metrics_values():
    y = np.array([1, 1, 1, 0, 0, 0, 0, 0])
    pred = np.array([1, 1, 0, 1, 0, 0, 0, 0])
    m = binary_metrics(y, pred)
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (2, 1, 1, 4)
    assert np.isclose(m["precision"], 2 / 3) and np.isclose(m["recall"], 2 / 3)
    assert np.isclose(m["fpr"], 1 / 5) and np.isclose(m["fnr"], 1 / 3)


def _brute(y, s, forced, beta, max_fpr):
    best, best_t = -1, None
    for t in np.unique(s[~forced]):
        pred = forced | (s >= t)
        tp, fp = (pred & (y == 1)).sum(), (pred & (y == 0)).sum()
        fn = ((~pred) & (y == 1)).sum()
        if fp / (y == 0).sum() > max_fpr:
            continue
        f = (1 + beta ** 2) * tp / ((1 + beta ** 2) * tp + beta ** 2 * fn + fp)
        if f > best + 1e-12:
            best, best_t = f, t
    return best_t


def test_best_threshold_matches_bruteforce():
    rng = np.random.default_rng(0)
    y = (rng.random(600) < 0.1).astype(int)
    s = np.clip(rng.normal(0.3 + 0.4 * y, 0.2), 0, 1)
    forced = (rng.random(600) < 0.05) & (y == 1)
    for fpr in (0.05, 0.2):
        assert np.isclose(best_threshold(y, s, forced, 2.0, fpr), _brute(y, s, forced, 2.0, fpr))


def test_high_threshold_precision_target_and_disabled_case():
    y = np.array([0] * 90 + [1] * 10)
    s = np.r_[np.linspace(0, 0.5, 90), np.linspace(0.6, 1, 10)]
    t = high_threshold(y, s, None, 0.0, 0.9)
    pred = s >= t
    assert y[pred].mean() >= 0.9
    assert high_threshold(y, np.zeros(100), None, 0.0, 0.9) == 1.01


def test_hybrid_score_reproduces_hybrid_decision():
    ml, rules = np.array([0.9, 0.1, 0.2]), np.array([False, True, False])
    score = hybrid_score(ml, rules, 0.5)
    np.testing.assert_array_equal(score >= 0.5, rules | (ml >= 0.5))
