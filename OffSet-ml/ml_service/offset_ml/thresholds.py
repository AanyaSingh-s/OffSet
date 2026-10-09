"""Validation-based threshold selection."""
from __future__ import annotations

import numpy as np


def _sweep(y: np.ndarray, score: np.ndarray, forced: np.ndarray):
    """Counts as the ML threshold decreases. Rows in `forced` (rule rejects) are always positive."""
    free = ~forced
    ys, ss = y[free], score[free]
    order = np.argsort(-ss, kind="stable")
    ss, ys = ss[order], ys[order]
    last_of_tie = np.r_[ss[1:] != ss[:-1], True]
    tp_ml = np.cumsum(ys)[last_of_tie]
    fp_ml = np.cumsum(1 - ys)[last_of_tie]
    return ss[last_of_tie], tp_ml, fp_ml, int((y[forced] == 1).sum()), int((y[forced] == 0).sum()), int(y.sum())


def best_threshold(y: np.ndarray, score: np.ndarray, forced: np.ndarray | None = None, beta: float = 2.0,
                   max_fpr: float | None = None) -> float:
    """Threshold maximising F-beta of (forced OR score >= t) subject to FPR <= max_fpr.
    Ties go to the higher threshold. If no threshold meets the FPR cap, the lowest-FPR one is used."""
    forced = np.zeros(len(y), bool) if forced is None else forced.astype(bool)
    thr, tp_ml, fp_ml, tp_f, fp_f, positives = _sweep(y.astype(int), score, forced)
    tp, fp = tp_ml + tp_f, fp_ml + fp_f
    fn = positives - tp
    b2 = beta ** 2
    f = (1 + b2) * tp / np.maximum((1 + b2) * tp + b2 * fn + fp, 1e-12)
    if max_fpr is not None:
        fpr = fp / max(int((y == 0).sum()), 1)
        feasible = fpr <= max_fpr
        f = np.where(feasible, f, -1.0) if feasible.any() else -fpr
    return float(thr[int(np.flatnonzero(f == f.max())[0])])


def high_threshold(y: np.ndarray, score: np.ndarray, forced: np.ndarray | None, floor: float,
                   min_precision: float) -> float:
    """Lowest threshold >= floor whose ML-only alerts (among rule-passing rows) reach min_precision.
    Returns 1.01 (HIGH disabled) when the precision target is unreachable on validation data."""
    forced = np.zeros(len(y), bool) if forced is None else forced.astype(bool)
    thr, tp_ml, fp_ml, *_ = _sweep(y.astype(int), score, forced)
    precision = tp_ml / np.maximum(tp_ml + fp_ml, 1)
    ok = (thr >= floor) & (precision >= min_precision) & (tp_ml >= 5)
    return float(thr[ok].min()) if ok.any() else 1.01
