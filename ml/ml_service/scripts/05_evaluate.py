"""Evaluate on held-out test users: Rules vs ML vs Hybrid, per scenario, unseen scenarios, latency.

Unseen-scenario (leave-one-scenario-out) runs retrain every model per scenario and are the slow part.
They can be split across invocations with --loso-scenarios; results are cached in reports/loso_parts/.
"""
import argparse
import json

import pandas as pd

from _bootstrap import ensure_project_imports

ensure_project_imports()

from OffSet.ml_service.offset_ml import evaluate as ev
from OffSet.ml_service.offset_ml.config import data_dir, load_config, models_dir, reports_dir
from OffSet.ml_service.offset_ml.logging_utils import get_logger
from OffSet.ml_service.offset_ml.results import load_result
from OffSet.ml_service.offset_ml.service.scoring import Scorer

log = get_logger("05_evaluate")


def run_loso(df, cfg, tiers, scenarios, parts) -> None:
    for tier in tiers:
        res = load_result(df, tier)
        for sc in scenarios:
            path = parts / f"{tier}_{sc}.csv"
            if not path.exists():
                ev.loso_table(df, cfg, tier, res, [sc]).to_csv(path, index=False)


def merge_loso(tiers, parts, out) -> None:
    for tier in tiers:
        files = [parts / f"{tier}_{sc}.csv" for sc in ev.SCENARIOS]
        if all(f.exists() for f in files):
            pd.concat([pd.read_csv(f) for f in files]).to_csv(out / f"loso_{tier}.csv", index=False)
        else:
            log.warning("[%s] unseen-scenario parts incomplete; rerun with --loso-scenarios", tier)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--tiers", default="native,extended")
    ap.add_argument("--skip-loso", action="store_true")
    ap.add_argument("--loso-only", action="store_true")
    ap.add_argument("--loso-scenarios", default=",".join(ev.SCENARIOS))
    args = ap.parse_args()
    cfg = load_config(args.config)
    tiers = args.tiers.split(",")
    df = pd.read_csv(data_dir() / "features.csv.gz", keep_default_na=False, na_values=[])
    out = reports_dir()
    parts = out / "loso_parts"
    parts.mkdir(exist_ok=True)

    if not args.skip_loso:
        run_loso(df, cfg, tiers, args.loso_scenarios.split(","), parts)
        merge_loso(tiers, parts, out)
    if args.loso_only:
        return

    raw = pd.read_csv(data_dir() / "raw.csv.gz", keep_default_na=False, na_values=[])
    summary = {}
    for tier in tiers:
        res = load_result(df, tier)
        overall = ev.overall_table(res, df)
        overall.to_csv(out / f"overall_{tier}.csv", index=False)
        ev.residual_table(res, df).to_csv(out / f"residual_{tier}.csv", index=False)
        ev.bootstrap_table(res, df).to_csv(out / f"bootstrap_ci_{tier}.csv", index=False)
        ev.scenario_table(res, df).to_csv(out / f"scenario_{tier}.csv", index=False)
        ev.risk_level_table(res, df).to_csv(out / f"risk_levels_{tier}.csv", index=False)
        summary[tier] = {"selected_model": res.selected, "thresholds": res.thresholds}
        log.info("[%s]\n%s", tier, overall[["system", "precision", "recall", "f1", "fpr", "roc_auc", "pr_auc"]].round(3).to_string())
    test_ids = set(df[df.split == "test"].tx_id)
    scorer = Scorer.from_dir(models_dir(), cfg)
    summary["latency_ms"] = ev.latency_ms(scorer, raw[raw.tx_id.isin(test_ids)])
    (out / "evaluation_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    log.info("latency: %s", summary["latency_ms"])


if __name__ == "__main__":
    main()
