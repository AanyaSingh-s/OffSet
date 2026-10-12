from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def binary_metrics(y: np.ndarray, pred: np.ndarray) -> dict:
    y, pred = np.asarray(y).astype(bool), np.asarray(pred).astype(bool)
    tp, fp = int((y & pred).sum()), int((~y & pred).sum())
    fn, tn = int((y & ~pred).sum()), int((~y & ~pred).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": prec, "recall": rec,
        "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "fpr": fp / (fp + tn) if fp + tn else 0.0,
        "fnr": fn / (fn + tp) if fn + tp else 0.0,
        "accuracy": (tp + tn) / len(y),
    }


def rank_metrics(y: np.ndarray, score: np.ndarray) -> dict:
    y = np.asarray(y)
    if y.min() == y.max():
        return {"roc_auc": float("nan"), "pr_auc": float("nan")}
    return {"roc_auc": float(roc_auc_score(y, score)), "pr_auc": float(average_precision_score(y, score))}


def hybrid_score(ml_score: np.ndarray, rule_reject: np.ndarray, alert_threshold: float) -> np.ndarray:
    """Continuous score of the hybrid system: a rule reject is lifted to at least the alert threshold,
    so thresholding at alert_threshold reproduces the hybrid decision and curves stay well defined."""
    return np.where(rule_reject, np.maximum(ml_score, alert_threshold), ml_score)
