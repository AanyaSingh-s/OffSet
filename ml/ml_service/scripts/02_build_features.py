"""Build causal features + rule verdicts + user-level split: data/features.csv.gz."""
import argparse

import pandas as pd

from _bootstrap import ensure_project_imports

ensure_project_imports()

from OffSet.ml_service.offset_ml.config import data_dir, load_config
from OffSet.ml_service.offset_ml.pipeline import build_features
from OffSet.ml_service.offset_ml.split import add_split


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    raw = pd.read_csv(data_dir() / "raw.csv.gz", keep_default_na=False, na_values=[])
    users = pd.read_csv(data_dir() / "users.csv")
    feats = add_split(build_features(raw, users, cfg), users, cfg.split)
    feats.to_csv(data_dir() / "features.csv.gz", index=False)


if __name__ == "__main__":
    main()
