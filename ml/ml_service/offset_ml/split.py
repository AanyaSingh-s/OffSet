"""User-level split stratified by archetype, so no user appears in more than one partition."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import SplitConfig


def assign_split(users: pd.DataFrame, cfg: SplitConfig) -> dict[str, str]:
    rng = np.random.default_rng(cfg.seed)
    mapping: dict[str, str] = {}
    for _, grp in users.groupby("archetype"):
        ids = grp["user_id"].to_numpy()
        rng.shuffle(ids)
        n_tr, n_va = int(round(len(ids) * cfg.train)), int(round(len(ids) * cfg.val))
        for i, uid in enumerate(ids):
            mapping[uid] = "train" if i < n_tr else "val" if i < n_tr + n_va else "test"
    return mapping


def add_split(df: pd.DataFrame, users: pd.DataFrame, cfg: SplitConfig) -> pd.DataFrame:
    out = df.copy()
    out["split"] = out["user_id"].map(assign_split(users, cfg))
    return out
