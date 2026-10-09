"""Inference core shared by the API and the latency benchmark. Never trains or refits anything."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .. import rules
from ..config import Config
from ..events import TxEvent
from ..features import compute_features
from ..logging_utils import get_logger
from ..models import risk_score
from ..persistence import load_bundle
from ..state import StateStore

log = get_logger("scoring")


@dataclass
class Assessment:
    risk_score: float
    risk_level: str
    action: str
    model_version: str
    feature_tier: str
    policy_violations: list[str] = field(default_factory=list)


class Scorer:
    def __init__(self, bundles: dict[str, tuple[object, dict]], cfg: Config,
                 medium: float | None = None, high: float | None = None):
        if not bundles:
            raise ValueError("at least one model bundle is required")
        self.bundles, self.cfg = bundles, cfg
        self.medium, self.high = medium, high
        self.store = StateStore(cfg.generator.tz_offset_s)
        self.lock = threading.Lock()
        for model, meta in bundles.values():
            if hasattr(model, "n_jobs"):
                model.n_jobs = 1

    @classmethod
    def from_dir(cls, model_dir: Path, cfg: Config, medium: float | None = None, high: float | None = None) -> "Scorer":
        bundles = {}
        for tier in ("native", "extended"):
            path = model_dir / f"deploy_{tier}.joblib"
            if path.exists():
                bundles[tier] = load_bundle(path)
        if not bundles:
            raise FileNotFoundError(f"no deploy_*.joblib bundles in {model_dir}; run scripts/04_train.py")
        return cls(bundles, cfg, medium, high)

    def _level(self, score: float, thresholds: dict) -> str:
        medium = self.medium if self.medium is not None else thresholds["medium"]
        high = self.high if self.high is not None else thresholds["high"]
        return "HIGH" if score >= high else "MEDIUM" if score >= medium else "LOW"

    def assess(self, ev: TxEvent) -> Assessment:
        tier = "extended" if ev.device is not None and "extended" in self.bundles else "native"
        model, meta = self.bundles[tier]
        view = ev if tier == "extended" else ev.without_device()
        with self.lock:
            st = self.store.get(ev.user_id)
            flags = rules.evaluate(view, st, self.cfg.policy)
            feats = compute_features(view, st, self.cfg.features)
            x = np.array([[feats[f] for f in meta["features"]]], dtype=float)
            score = float(risk_score(meta["model_name"], model, x)[0])
            st.update(view, settled=not rules.native_reject(flags))
        active = rules.ALL_RULES if tier == "extended" else rules.NATIVE_RULES
        violations = [r for r in active if flags[r]]
        level = self._level(score, meta["thresholds"])
        if violations:
            action = "REJECT"
        elif level in self.cfg.service.flag_levels:
            action = "FLAG"
        else:
            action = "ACCEPT"
        return Assessment(round(score, 6), level, action, meta["model_version"], tier, violations)
