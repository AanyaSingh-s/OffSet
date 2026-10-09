# Dataset validation report

| Check | Result | Detail |
|---|---|---|
| post = pre - amount (all rows) | PASS |  |
| server balance never negative | PASS |  |
| settled amount <= server balance before | PASS |  |
| sync_lag >= 0 | PASS | min=0.57 min |
| legit rows carry no scenario | PASS |  |
| fraud rows all carry a scenario | PASS |  |
| legit chain: next_pre == previous_post within an offline window | PASS | 107126 pairs |
| first legit tx of an offline window starts at last synced server balance | PASS | 79322 rows |
| double-spend: same pre-balance and combined amount exceeds it | PASS | 142 attacks |
| duplicates reuse an earlier packet hash | PASS | 28 duplicates |
| legitimate repeated payee+amount payments exist and are not fraud | PASS | 40898 repeated (user,payee,amount) groups |
| ledger outcome == native-rule verdict | PASS |  |

## Summary

```
rows: 194514
users: 3000
fraud_rows: 8066
fraud_rate: 0.041467452214236505
fraud_attacks: 2059
outcomes: {'SETTLED': 193137, 'REJECTED': 1349, 'DUPLICATE': 28}
scenario_rows: {'velocity_burst': 3019, 'cumulative_offline_spend': 2267, 'long_offline_suspicious': 648, 'combined': 555, 'device_change': 416, 'rollback': 344, 'new_beneficiary_unusual_amount': 267, 'replay_duplicate': 222, 'large_amount': 186, 'double_spend': 142}
legit_rejected_by_native_rules: 897
sync_lag_min_quantiles_legit: {0.5: 56.0, 0.9: 284.9, 0.99: 869.1}
sync_lag_min_quantiles_fraud: {0.5: 44.5, 0.9: 212.2, 0.99: 67138.7}
legit_lag_over_1h_share: 0.4791845447524243
```

## Split sizes

| split   |   rows |   users |   fraud |
|:--------|-------:|--------:|--------:|
| test    |  40207 |     599 |    1817 |
| train   | 115692 |    1801 |    4548 |
| val     |  38615 |     600 |    1701 |