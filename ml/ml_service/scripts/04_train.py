"""Train LR / RF / Isolation Forest per feature tier, choose thresholds on validation, persist models."""
import argparse
import json

import joblib
import pandas as pd

from _bootstrap import ensure_project_imports

ensure_project_imports()

from OffSet.ml_service.offset_ml.config import data_dir, load_config, models_dir
from OffSet.ml_service.offset_ml.persistence import save_bundle
from OffSet.ml_service.offset_ml.training import bundle_meta, fit_tier


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    df = pd.read_csv(data_dir() / "features.csv.gz", keep_default_na=False, na_values=[])
    out = models_dir()
    for tier in ("native", "extended"):
        res = fit_tier(df, cfg, tier)
        meta = bundle_meta(res, cfg)
        save_bundle(out / f"deploy_{tier}.joblib", res.models[res.selected], meta)
        joblib.dump({"models": res.models, "thresholds": res.thresholds, "selected": res.selected},
                    out / f"all_models_{tier}.joblib", compress=3)
        (out / f"thresholds_{tier}.json").write_text(json.dumps(
            {"selected": res.selected, "thresholds": res.thresholds, "validation": res.val_summary}, indent=2))


if __name__ == "__main__":
    main()
