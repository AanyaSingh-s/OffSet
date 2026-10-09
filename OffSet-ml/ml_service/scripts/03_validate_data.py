"""Run consistency checks on raw data and features; writes reports/dataset_report.md. Exits non-zero on failure."""
import argparse
import sys

import pandas as pd

from OffSet.ml_service.offset_ml.config import data_dir, load_config, reports_dir
from OffSet.ml_service.offset_ml.data.validate import check_dataset


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    raw = pd.read_csv(data_dir() / "raw.csv.gz", keep_default_na=False, na_values=[])
    feats = pd.read_csv(data_dir() / "features.csv.gz", keep_default_na=False, na_values=[])
    checks, summary = check_dataset(raw, feats, cfg)
    lines = ["# Dataset validation report", "", "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {'PASS' if ok else 'FAIL'} | {d} |" for n, ok, d in checks]
    lines += ["", "## Summary", "", "```"] + [f"{k}: {v}" for k, v in summary.items()] + ["```"]
    split_tbl = feats.groupby("split").agg(rows=("tx_id", "size"), users=("user_id", "nunique"),
                                           fraud=("fraud_label", "sum"))
    lines += ["", "## Split sizes", "", split_tbl.to_markdown()]
    (reports_dir() / "dataset_report.md").write_text("\n".join(lines))
    print("\n".join(lines))
    sys.exit(0 if all(ok for _, ok, _ in checks) else 1)


if __name__ == "__main__":
    main()
