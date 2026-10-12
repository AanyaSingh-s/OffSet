"""Sanity checks that the synthetic data is internally consistent and the fraud labels are structural."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import Config
from ..rules import NATIVE_RULES


def check_dataset(raw: pd.DataFrame, feats: pd.DataFrame, cfg: Config) -> tuple[list[tuple[str, bool, str]], dict]:
    results: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, bool(ok), detail))

    add("post = pre - amount (all rows)",
        np.allclose(raw.local_post_balance, raw.local_pre_balance - raw.amount, atol=0.011))
    add("server balance never negative", (raw.server_balance_before >= 0).all())
    settled = raw[raw.outcome == "SETTLED"]
    add("settled amount <= server balance before", (settled.amount <= settled.server_balance_before + 0.011).all())
    add("sync_lag >= 0", (raw.sync_lag_min >= 0).all(), f"min={raw.sync_lag_min.min():.2f} min")
    add("legit rows carry no scenario", (raw[raw.fraud_label == 0].fraud_scenario == "").all())
    add("fraud rows all carry a scenario", (raw[raw.fraud_label == 1].fraud_scenario != "").all())

    legit = raw[(raw.fraud_label == 0) & (raw.outcome != "DUPLICATE")].sort_values(["user_id", "arrival_idx"])
    prev = legit.groupby("user_id").shift(1)
    same_chain = (prev.last_sync_at == legit.last_sync_at) & (legit.local_seq == prev.local_seq + 1)
    gap = (legit.local_pre_balance - prev.local_post_balance)[same_chain]
    add("legit chain: next_pre == previous_post within an offline window", (gap.abs() < 0.011).all(),
        f"{int(same_chain.sum())} pairs")
    first = legit[(legit.local_seq == legit.groupby(["user_id", "last_sync_at"]).local_seq.transform("min"))]
    add("first legit tx of an offline window starts at last synced server balance",
        np.allclose(first.local_pre_balance, first.last_synced_server_balance, atol=0.011), f"{len(first)} rows")

    ok, pairs = True, 0
    for aid, g in raw[raw.fraud_scenario == "double_spend"].groupby("attack_id"):
        second = g.iloc[0]
        first_leg = raw[(raw.user_id == second.user_id) & (raw.fraud_variant == "first_leg")
                        & (raw.local_pre_balance == second.local_pre_balance)]
        pairs += 1
        ok &= len(first_leg) >= 1 and (first_leg.amount.iloc[0] + second.amount > second.local_pre_balance)
    add("double-spend: same pre-balance and combined amount exceeds it", ok, f"{pairs} attacks")

    ordered = raw.sort_values(["user_id", "arrival_idx"])
    seen_before = ordered.groupby(["user_id", "packet_hash"]).cumcount() > 0
    dup = ordered[ordered.outcome == "DUPLICATE"]
    add("duplicates reuse an earlier packet hash", seen_before.loc[dup.index].all(), f"{len(dup)} duplicates")

    repeats = legit.groupby(["user_id", "receiver_id", "amount"]).size()
    add("legitimate repeated payee+amount payments exist and are not fraud",
        (repeats > 1).sum() > 0, f"{int((repeats > 1).sum())} repeated (user,payee,amount) groups")

    ledger_native = feats.set_index("tx_id").loc[raw.tx_id]
    rule_out = np.where(ledger_native.N_DUPLICATE_PACKET, "DUPLICATE",
                        np.where(ledger_native[list(NATIVE_RULES)].any(axis=1), "REJECTED", "SETTLED"))
    add("ledger outcome == native-rule verdict", (rule_out == raw.outcome.to_numpy()).all())

    summary = {
        "rows": int(len(raw)), "users": int(raw.user_id.nunique()),
        "fraud_rows": int(raw.fraud_label.sum()), "fraud_rate": float(raw.fraud_label.mean()),
        "fraud_attacks": int(raw[raw.attack_id > 0].attack_id.nunique()),
        "outcomes": raw.outcome.value_counts().to_dict(),
        "scenario_rows": raw[raw.fraud_label == 1].fraud_scenario.value_counts().to_dict(),
        "legit_rejected_by_native_rules": int(((raw.fraud_label == 0) & (raw.outcome != "SETTLED")).sum()),
        "sync_lag_min_quantiles_legit": raw[raw.fraud_label == 0].sync_lag_min.quantile([.5, .9, .99]).round(1).to_dict(),
        "sync_lag_min_quantiles_fraud": raw[raw.fraud_label == 1].sync_lag_min.quantile([.5, .9, .99]).round(1).to_dict(),
        "legit_lag_over_1h_share": float((raw[raw.fraud_label == 0].sync_lag_min > 60).mean()),
    }
    return results, summary
