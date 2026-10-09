"""Test-set evaluation: Rules vs ML vs Hybrid, per-scenario, unseen-scenario (leave-one-scenario-out), latency."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from .config import Config
from .events import TxEvent
from .features import TIERS
from .logging_utils import get_logger
from .metrics import binary_metrics, hybrid_score, rank_metrics
from .models import MODEL_NAMES, fit_model, risk_score
from .thresholds import best_threshold
from .training import TierResult, rule_column, split_arrays

log = get_logger("evaluate")
SCENARIOS = ["rollback", "double_spend", "velocity_burst", "large_amount", "new_beneficiary_unusual_amount",
             "device_change", "long_offline_suspicious", "cumulative_offline_spend", "replay_duplicate", "combined"]


def system_predictions(res: TierResult, test_rules: np.ndarray) -> dict[str, np.ndarray]:
    """Binary alert vector for each system on the test split."""
    preds = {"rules_only": test_rules}
    for name in res.models:
        s, th = res.scores[name]["test"], res.thresholds[name]
        preds[f"ml_{name}"] = s >= th["ml_only"]
        preds[f"hybrid_{name}"] = test_rules | (s >= th["hybrid"])
    return preds


def overall_table(res: TierResult, df: pd.DataFrame) -> pd.DataFrame:
    _, y, r, _ = split_arrays(df, res.tier)["test"]
    preds = system_predictions(res, r)
    rows = []
    for system, pred in preds.items():
        row = {"system": system, **binary_metrics(y, pred)}
        if system == "rules_only":
            row.update(roc_auc=float("nan"), pr_auc=float("nan"))
        elif system.startswith("ml_"):
            row.update(rank_metrics(y, res.scores[system[3:]]["test"]))
        else:
            row.update(rank_metrics(y, hybrid_score(res.scores[system[7:]]["test"], r, res.thresholds[system[7:]]["hybrid"])))
        rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_table(res: TierResult, df: pd.DataFrame, n_boot: int = 300, seed: int = 0) -> pd.DataFrame:
    """95% percentile CIs from resampling test users (clusters) with replacement."""
    _, y, r, part = split_arrays(df, res.tier)["test"]
    y = y.astype(bool)
    _, inv = np.unique(part.user_id.to_numpy(), return_inverse=True)
    n_users = inv.max() + 1
    idx = np.random.default_rng(seed).integers(0, n_users, (n_boot, n_users))
    rows = []
    for system, pred in system_predictions(res, r).items():
        cells = ((y & pred), (~y & pred), (y & ~pred), (~y & ~pred))
        counts = np.stack([np.bincount(inv, weights=c.astype(float), minlength=n_users) for c in cells], axis=1)
        tp, fp, fn, tn = counts[idx].sum(axis=1).T
        prec, rec = tp / np.maximum(tp + fp, 1), tp / np.maximum(tp + fn, 1)
        stats = {"precision": prec, "recall": rec, "f1": 2 * prec * rec / np.maximum(prec + rec, 1e-12),
                 "fpr": fp / np.maximum(fp + tn, 1)}
        row = {"system": system}
        for k, v in stats.items():
            lo, hi = np.percentile(v, [2.5, 97.5])
            row.update({f"{k}_lo": lo, f"{k}_hi": hi})
        rows.append(row)
    return pd.DataFrame(rows)


def residual_table(res: TierResult, df: pd.DataFrame) -> pd.DataFrame:
    """Performance of each ML model only on test rows that pass the deterministic rules."""
    _, y, r, _ = split_arrays(df, res.tier)["test"]
    keep = ~r
    rows = []
    for name in res.models:
        s = res.scores[name]["test"][keep]
        pred = s >= res.thresholds[name]["hybrid"]
        rows.append({"model": name, "residual_rows": int(keep.sum()), "residual_fraud": int(y[keep].sum()),
                     **binary_metrics(y[keep], pred), **rank_metrics(y[keep], s)})
    return pd.DataFrame(rows)


def scenario_table(res: TierResult, df: pd.DataFrame) -> pd.DataFrame:
    _, y, r, part = split_arrays(df, res.tier)["test"]
    preds = system_predictions(res, r)
    legit = y == 0
    rows = []
    for system, pred in preds.items():
        fp = int((pred & legit).sum())
        for sc in SCENARIOS:
            m = (part.fraud_scenario == sc).to_numpy()
            tp = int((pred & m).sum())
            fn = int(m.sum()) - tp
            attacks = part[m].assign(hit=pred[m]).groupby("attack_id").hit.any()
            rows.append({"system": system, "scenario": sc, "n": int(m.sum()), "recall": tp / max(m.sum(), 1),
                         "f1": 2 * tp / max(2 * tp + fp + fn, 1), "attack_recall": float(attacks.mean()),
                         "attacks": int(len(attacks))})
    return pd.DataFrame(rows)


def loso_table(df: pd.DataFrame, cfg: Config, tier: str, seen: TierResult,
               scenarios: list[str] | None = None) -> pd.DataFrame:
    """Unseen-scenario test: drop every fraud row of one scenario from train and validation, then evaluate on it."""
    data = split_arrays(df, tier)
    Xtr, ytr, _, ptr = data["train"]
    Xva, yva, rva, pva = data["val"]
    Xte, yte, rte, pte = data["test"]
    rows = []
    for sc in scenarios or SCENARIOS:
        keep_tr = ~((ptr.fraud_scenario == sc).to_numpy())
        keep_va = ~((pva.fraud_scenario == sc).to_numpy())
        target = (pte.fraud_scenario == sc).to_numpy()
        eval_mask = target | (yte == 0)
        for name in MODEL_NAMES:
            model = fit_model(name, Xtr[keep_tr], ytr[keep_tr], cfg.model, cfg.model.loso_rf_trees)
            sv = risk_score(name, model, Xva[keep_va])
            t_ml = best_threshold(yva[keep_va], sv, None, cfg.model.f_beta, cfg.model.max_fpr)
            t_hy = best_threshold(yva[keep_va], sv, rva[keep_va], cfg.model.f_beta, cfg.model.max_fpr)
            st = risk_score(name, model, Xte)
            legit = yte == 0
            for system, pred in (("ml", st >= t_ml), ("hybrid", rte | (st >= t_hy))):
                rows.append({"scenario": sc, "model": name, "system": system, "mode": "unseen",
                             "recall": float(pred[target].mean()), "fpr": float(pred[legit].mean()),
                             "roc_auc": rank_metrics(yte[eval_mask], (st if system == "ml" else hybrid_score(st, rte, t_hy))[eval_mask])["roc_auc"]})
            log.info("LOSO %s / %s done", sc, name)
        seen_sc = system_predictions(seen, rte)
        for name in MODEL_NAMES:
            for system, key in (("ml", f"ml_{name}"), ("hybrid", f"hybrid_{name}")):
                pred = seen_sc[key]
                rows.append({"scenario": sc, "model": name, "system": system, "mode": "seen",
                             "recall": float(pred[target].mean()), "fpr": float(pred[yte == 0].mean()), "roc_auc": np.nan})
        rows.append({"scenario": sc, "model": "rules", "system": "rules", "mode": "n/a",
                     "recall": float(rte[target].mean()), "fpr": float(rte[yte == 0].mean()), "roc_auc": np.nan})
    return pd.DataFrame(rows)


def risk_level_table(res: TierResult, df: pd.DataFrame) -> pd.DataFrame:
    _, y, r, _ = split_arrays(df, res.tier)["test"]
    s = res.scores[res.selected]["test"]
    t = res.thresholds[res.selected]
    level = np.where(s >= t["high"], "HIGH", np.where(s >= t["hybrid"], "MEDIUM", "LOW"))
    rows = []
    for lv in ("LOW", "MEDIUM", "HIGH"):
        m = (level == lv) & ~r
        rows.append({"risk_level": lv, "rows": int(m.sum()), "fraud": int(y[m].sum()),
                     "fraud_share": float(y[m].mean()) if m.any() else float("nan")})
    return pd.DataFrame(rows)


def latency_ms(scorer, raw_test: pd.DataFrame, limit: int = 3000) -> dict:
    """Latency of one full assessment (rules + features + model) through the serving code path."""
    from .pipeline import row_to_event
    events = [row_to_event(r) for r in raw_test.sort_values(["user_id", "arrival_idx"]).head(limit).itertuples(index=False)]
    for ev in events[:50]:
        scorer.assess(ev)
    times = []
    for ev in events[50:]:
        t0 = time.perf_counter()
        scorer.assess(ev)
        times.append((time.perf_counter() - t0) * 1000)
    arr = np.array(times)
    return {"n": len(arr), "mean_ms": float(arr.mean()), "p50_ms": float(np.percentile(arr, 50)),
            "p95_ms": float(np.percentile(arr, 95)), "p99_ms": float(np.percentile(arr, 99))}
