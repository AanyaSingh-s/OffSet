"""Create all paper figures into figures/ (PDF + PNG)."""
import argparse

import pandas as pd

from _bootstrap import ensure_project_imports

ensure_project_imports()

from OffSet.ml_service.offset_ml import figures as fg
from OffSet.ml_service.offset_ml.config import data_dir, load_config, reports_dir
from OffSet.ml_service.offset_ml.evaluate import overall_table, scenario_table
from OffSet.ml_service.offset_ml.features import DEVICE_FEATURES, NATIVE_FEATURES
from OffSet.ml_service.offset_ml.logging_utils import get_logger
from OffSet.ml_service.offset_ml.results import load_result

log = get_logger("06_figures")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    fg.style()
    df = pd.read_csv(data_dir() / "features.csv.gz", keep_default_na=False, na_values=[])
    res = {t: load_result(df, t) for t in ("native", "extended")}
    ext = res["extended"]
    fg.confusion(ext, df)
    fg.roc_pr(ext, df)
    imp = fg.importance(ext, df)
    imp.to_csv(reports_dir() / "feature_importance_extended.csv", index=False)
    fg.isolation(ext, df)
    fg.pipeline_diagram(len(NATIVE_FEATURES), len(DEVICE_FEATURES))
    fg.scenario_performance(ext, scenario_table(ext, df))
    fg.model_comparison({t: overall_table(r, df) for t, r in res.items()}, {t: r.selected for t, r in res.items()})
    fg.behaviour(df)
    fg.threshold_analysis(ext, df, cfg.model.f_beta)
    for tier in res:
        path = reports_dir() / f"loso_{tier}.csv"
        if path.exists():
            fg.unseen(pd.read_csv(path), tier)
        else:
            log.warning("%s missing; run scripts/05_evaluate.py without --skip-loso for the unseen-scenario figure", path.name)
    log.info("figures written")


if __name__ == "__main__":
    main()
