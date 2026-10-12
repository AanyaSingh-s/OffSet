"""Training and validation-based selection for one feature tier."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import Config
from .features import TIERS
from .logging_utils import get_logger
from .metrics import binary_metrics, rank_metrics
from .models import MODEL_NAMES, fit_model, risk_score
from .persistence import model_version
from .thresholds import best_threshold, high_threshold

log = get_logger("training")


def rule_column(tier: str) -> str:
    return "rules_native_reject" if tier == "native" else "rules_policy_reject"


@dataclass
class TierResult:
    tier: str
    features: list[str]
    models: dict
    scores: dict[str, dict[str, np.ndarray]]      # model -> split -> score
    thresholds: dict[str, dict[str, float]]       # model -> {ml_only, hybrid, high}
    val_summary: dict[str, dict[str, float]]
    selected: str


def split_arrays(df: pd.DataFrame, tier: str):
    cols = TIERS[tier]
    out = {}
    for name in ("train", "val", "test"):
        part = df[df.split == name]
        out[name] = (part[cols].to_numpy(float), part.fraud_label.to_numpy(int),
                     part[rule_column(tier)].to_numpy(bool), part)
    return out


def fit_tier(df: pd.DataFrame, cfg: Config, tier: str, rf_trees: int | None = None,
             names: tuple[str, ...] = MODEL_NAMES) -> TierResult:
    data = split_arrays(df, tier)
    Xtr, ytr, _, _ = data["train"]
    Xva, yva, rva, _ = data["val"]
    models, scores, thresholds, val_summary = {}, {}, {}, {}
    for name in names:
        model = fit_model(name, Xtr, ytr, cfg.model, rf_trees)
        models[name] = model
        scores[name] = {s: risk_score(name, model, data[s][0]) for s in data}
        sv = scores[name]["val"]
        t_ml = best_threshold(yva, sv, None, cfg.model.f_beta, cfg.model.max_fpr)
        t_hy = best_threshold(yva, sv, rva, cfg.model.f_beta, cfg.model.max_fpr)
        t_hi = high_threshold(yva, sv, rva, t_hy, cfg.model.high_precision)
        thresholds[name] = {"ml_only": t_ml, "hybrid": t_hy, "high": t_hi}
        hy_pred = rva | (sv >= t_hy)
        hy = binary_metrics(yva, hy_pred)
        beta2 = cfg.model.f_beta ** 2
        fbeta = (1 + beta2) * hy["tp"] / max((1 + beta2) * hy["tp"] + beta2 * hy["fn"] + hy["fp"], 1e-12)
        val_summary[name] = {"val_pr_auc": rank_metrics(yva, sv)["pr_auc"], "val_hybrid_fbeta": fbeta,
                             "val_hybrid_recall": hy["recall"], "val_hybrid_fpr": hy["fpr"]}
    selected = max(val_summary, key=lambda n: val_summary[n]["val_hybrid_fbeta"])
    log.info("[%s] selected %s by validation hybrid F%.0f: %s", tier, selected, cfg.model.f_beta,
             {k: round(v["val_hybrid_fbeta"], 4) for k, v in val_summary.items()})
    return TierResult(tier, TIERS[tier], models, scores, thresholds, val_summary, selected)


def bundle_meta(res: TierResult, cfg: Config) -> dict:
    t = res.thresholds[res.selected]
    return {
        "tier": res.tier, "model_name": res.selected, "features": res.features,
        "model_version": model_version(res.selected, res.tier, res.features, cfg.model.seed),
        "thresholds": {"medium": t["hybrid"], "high": t["high"]},
        "ml_only_threshold": t["ml_only"],
        "validation": res.val_summary,
        "beta": cfg.model.f_beta, "max_fpr": cfg.model.max_fpr, "high_precision_target": cfg.model.high_precision,
        "policy": vars(cfg.policy),
    }
