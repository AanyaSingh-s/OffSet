"""Load persisted models and recompute scores for a feature table."""
from __future__ import annotations

import joblib
import pandas as pd

from .config import models_dir
from .features import TIERS
from .models import risk_score
from .training import TierResult, split_arrays


def load_result(df: pd.DataFrame, tier: str) -> TierResult:
    blob = joblib.load(models_dir() / f"all_models_{tier}.joblib")
    data = split_arrays(df, tier)
    scores = {n: {s: risk_score(n, m, data[s][0]) for s in data} for n, m in blob["models"].items()}
    return TierResult(tier, TIERS[tier], blob["models"], scores, blob["thresholds"], {}, blob["selected"])
