"""Model factory. Every model exposes a risk score where higher means more suspicious."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import ModelConfig

MODEL_NAMES = ("logistic_regression", "random_forest", "isolation_forest")
SUPERVISED = ("logistic_regression", "random_forest")


def make_model(name: str, cfg: ModelConfig, rf_trees: int | None = None):
    if name == "logistic_regression":
        return make_pipeline(StandardScaler(), LogisticRegression(
            C=cfg.lr_c, class_weight="balanced", max_iter=3000, random_state=cfg.seed))
    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=rf_trees or cfg.rf_trees, min_samples_leaf=cfg.rf_min_leaf,
            class_weight="balanced_subsample", n_jobs=-1, random_state=cfg.seed)
    if name == "isolation_forest":
        return IsolationForest(n_estimators=cfg.if_trees, max_samples=cfg.if_max_samples,
                               contamination="auto", random_state=cfg.seed, n_jobs=-1)
    raise ValueError(f"unknown model '{name}'")


def fit_model(name: str, X: np.ndarray, y: np.ndarray, cfg: ModelConfig, rf_trees: int | None = None):
    """Supervised models use labels; Isolation Forest is fitted unsupervised on all training rows."""
    model = make_model(name, cfg, rf_trees)
    if name == "isolation_forest":
        model.fit(X)
    else:
        model.fit(X, y)
    return model


def risk_score(name: str, model, X: np.ndarray) -> np.ndarray:
    """Probability of fraud for supervised models; Isolation Forest anomaly score s(x)=2^(-E[h(x)]/c(psi)) in (0,1]."""
    if name == "isolation_forest":
        return -model.score_samples(X)
    return model.predict_proba(X)[:, 1]
