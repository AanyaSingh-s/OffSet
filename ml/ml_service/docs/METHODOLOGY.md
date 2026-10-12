# Methodology and results notes

## 1. What the repository supports

| Item in the task brief | In the repository? | Handling |
|---|---|---|
| Idempotency (ciphertext hash), freshness window (24 h, 5 min future skew), sender balance check | Yes | Native rules, mirrored in `rules.py` and `ledger.py` |
| Amount, sender/receiver VPA, signed time, settlement time, nonce | Yes | Native features |
| Account balance and version | Yes (server side) | `server_balance`, `server_version` |
| Per-transaction, daily, velocity, offline-duration limits | No | Proposed policy rules (`X_*`), configurable |
| Separate nonce store | No (only the ciphertext hash) | Proposed rule `X_NONCE_REUSE` |
| Local device balance, sequence counter, device id, snapshot version, last sync time | No | Proposed optional payload fields (extended tier) |
| Location, merchant category, transaction type, authentication failures | No | Omitted. No location scenario was generated |
| Sender authentication | PIN hash is carried but, as read, not verified; no signature check | Out of scope for ML; stated as a limitation |

Two tiers follow from this. **Native**: repo-native rules and 29 features. **Extended**: adds the policy rules and
8 device-state features (37 total) and needs the five extra payload fields.

## 2. Synthetic data

Fully synthetic: no real statements or histories. Defaults: 3,000 users, 180 days, 194,514 transactions, 4.15% fraud rows (a generator
setting, not a real-world rate).

- **Users:** five archetypes (frequent low-value, occasional, larger-payment, merchant-heavy, transfer-heavy), each with persistent
  rate, median amount, favourite payees (Zipf weights), peak hour with circadian concentration, weekday/weekend factor and target balance.
- **Outages:** a user is offline in outage episodes (rate about 0.4/day, lognormal duration, median 45 min, capped at 11 h). Payments arrive by thinning a
  Poisson process with the user's hourly activity.
- **Device state:** `local_post = local_pre - amount`; within an offline window `next_pre = previous_post`; the first payment starts at
  the last synced server balance. Both are checked by `03_validate_data.py`.
- **Server state:** a ledger settles each batch in synchronisation order using the native rules only. The balance never goes negative.
  `sync_lag = sync_at - signed_at`; 8% of batches sync late (lognormal, median 4 h), so long lag alone is not fraud.
- **Legitimate hard cases:** group-meal bursts, new payees (7%), large purchases (2%), device changes (1% of episodes, persistent),
  repeated payee and amount, and other-channel debits that make a legitimate payment fail the balance check.
- **Fraud scenarios (10):** rollback, double spend, velocity burst, large amount, new beneficiary with unusual amount, device change,
  long offline with suspicious spending, cumulative offline spend, replay/duplicate, combined multi-signal. Many have an "evasive" variant
  that stays under the policy limits. Attack events are appended after the episode's legitimate payments, so state chains stay ordered.
- **Labels:** every transaction of an attack is labelled fraud, except the first leg of a double spend (a valid payment; only the conflicting
  second leg is fraud). A pure device change without other signals is not labelled fraud.

## 3. Features

All features use the event itself and the user's earlier state only (`state.py`, `features.py`). State is updated after scoring, and only
for payments the native rules accepted.

- Welford update of the mean and variance of ln(amount): `d = x - m; m += d/n; M2 += d(x - m)`; sample std `sqrt(M2/(n-1))`.
- Amount z-score: `(ln a - mean_ln) / max(std_ln, 0.1)`, clipped to ±10; set to 0 when fewer than 5 prior payments (`is_cold_start = 1`).
- Window counts over `[s - w, s)` for 10 min, 1 h, 24 h; calendar-day count and spend (IST), including the current amount.
- `queue_depth`, `queue_spend`: earlier payments whose sync time is after this payment's signing time (the device's unsent queue).
- Receiver familiarity and `is_new_receiver` (0 on a cold start); hour-of-day share `(k + 3*5/24)/(n + 3)` over a ±2 h window; weekday/weekend share, same smoothing.
- Extended: `chain_gap` (local pre minus previous post, only within the same offline window), `seq_gap`, `local_server_gap`, `snapshot_regress`,
  `snapshot_staleness`, offline minutes, `device_new`, `device_changed`.

## 4. Models and thresholds

- **Logistic regression** (standardised, balanced class weights), **random forest** (300 trees, balanced subsample), **Isolation Forest**
  (300 trees, 256 samples, fitted unsupervised on all training rows). No XGBoost/LightGBM: the data is small and tabular, and RF already
  performs well without adding a dependency.
- **Isolation Forest score:** `s(x) = 2^(-E[h(x)] / c(psi))`, where `h(x)` is the path length to isolate `x`, `psi` the subsample size and
  `c(n) = 2(ln(n-1) + 0.5772) - 2(n-1)/n` the average path length of an unsuccessful BST search. `s` near 1 means anomalous;
  `s` well below 0.5 means normal. scikit-learn's `score_samples` returns `-s`, so the code negates it.
- **Thresholds** are chosen on validation users only: maximise F2 (recall-weighted) subject to a 3% false-positive-rate cap, separately for ML-only
  and for the hybrid (rule rejects always count as alerts). The HIGH level is the lowest threshold with validation precision of at least 0.90.
  The 3% cap and beta = 2 are my operating assumptions; change them in `ModelConfig`. `fig11` shows the trade-off.
- **Deployed model:** the one with the best validation hybrid F2 per tier (random forest in both tiers on this data).
- Scores are ranking scores, not calibrated probabilities.

## 5. Evaluation design

- User-level split (60/20/20, stratified by archetype); no user appears in two partitions.
- Systems: A rules only; B ML only; C hybrid (`rules OR score >= t`). Rules are the native rules in the native tier and native plus policy in the extended tier.
- Hybrid ROC/PR score: a rule reject is lifted to at least the alert threshold, so thresholding reproduces the hybrid decision.
- Per-scenario recall, one-vs-legitimate F1 and attack-level recall (an attack counts as caught if any of its transactions alerts).
- 95% intervals come from resampling test users (300 draws).
- Unseen scenarios: for each scenario, remove its fraud rows from training and validation, refit, re-select thresholds, then test on that scenario.

## 6. Results (held-out test users, extended tier, random forest)

Full tables are in `reports/results.md`; figures in `figures/`.

| System | Precision | Recall | F1 | FPR | PR-AUC |
|---|---|---|---|---|---|
| A. Rules only | 0.732 | 0.313 | 0.439 | 0.005 | n/a |
| B. ML only (RF) | 0.589 | 0.835 | 0.691 | 0.028 | 0.830 |
| C. Hybrid (RF) | 0.571 | 0.836 | 0.679 | 0.030 | 0.830 |

- Test-user bootstrap 95% intervals for recall: rules 0.27 to 0.36; ML 0.80 to 0.87; hybrid 0.80 to 0.87.
- Hybrid recall is about 0.1 points above ML-only, and its F1 is slightly lower. The ML model already receives the state-consistency features,
  so on this data the rules add little recall on top of it. Their value is deterministic, explainable rejection of replays and double spends
  (recall 1.0 for both) and independence from the model.
- On the 1,248 rule-passing fraud rows the RF reaches recall 0.76, which is the part rules cannot cover.
- Native tier: rules recall 0.06, RF hybrid recall 0.77 at FPR 0.029. Without device-state fields the model still works, but rollback is weak (recall 0.35 on unseen).
- Isolation Forest is clearly weaker (extended hybrid recall 0.42). Supervised models win on scenarios they were trained on.
- Unseen scenarios (hybrid RF, extended): mean recall across the 10 scenarios drops to 0.67 (LR 0.60, IF 0.49) when the scenario is held out.
  Large amount falls from 0.85 to 0.38 and cumulative spend from 0.72 to 0.26. Double spend and replay stay at 1.0 because the rules catch them.
  Combined attacks hold up (0.89), because their components are seen.
- Risk levels on test (extended): HIGH has 89% fraud among rule-passing rows, MEDIUM 37%, LOW 0.8%.
- Latency of one assessment through the serving code path (single thread): mean 16 ms, p95 20 ms, p99 25 ms.
- Test sets have 23 to 793 fraud rows per scenario and 23 to 53 attacks, so per-scenario numbers are noisy.

## 7. Limitations

- All fraud behaviour comes from my own generator and rule thresholds. Results show the pipeline works against these scenarios, not how it
  performs on real fraud, and the rates and thresholds are not real-world estimates.
- Rule thresholds (limits of 1000/2500 INR, 10 tx/hour, 12 h) are my assumptions, fixed before looking at results. Changing them changes the rules-only numbers.
- Many generated honest devices are perfectly consistent, which makes state-consistency features stronger than they would be with real clock drift and client bugs.
- Open-loop evaluation: behavioural history updates from payments the native rules accepted, regardless of the ML decision.
- Arrival order per user is assumed to equal signing order, except for modelled replays. Real mesh delivery can reorder packets.
- The Java demo's simulated phones are not real devices; the five payload fields are not authenticated beyond the existing encryption.
- No location, merchant category or authentication-failure data. Online state is in memory (single process).
- A lower-recall native tier is the only option until the payload fields exist.

## 8. Future work

Persist per-user state (Redis or the database), calibrate scores, validate on real pilot data, add signed device attestations, study
drift, and review flagged payments with a human-in-the-loop workflow.
