"""Generate the synthetic dataset: data/raw.csv.gz and data/users.csv."""
import argparse

from OffSet.ml_service.offset_ml.config import data_dir, load_config
from OffSet.ml_service.offset_ml.data.generator import generate


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--users", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.users:
        cfg.generator.n_users = args.users
    if args.seed is not None:
        cfg.generator.seed = args.seed
    raw, users = generate(cfg)
    raw.to_csv(data_dir() / "raw.csv.gz", index=False)
    users.to_csv(data_dir() / "users.csv", index=False)


if __name__ == "__main__":
    main()
