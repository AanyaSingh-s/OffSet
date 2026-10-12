# OffSet ML service: behavioural fraud detection for offline payments

Adds a behavioural risk layer on top of the deterministic checks in the OffSet Spring Boot backend.
It never replaces them: the backend stays the decision authority and the ML call is fail-open.

```
Offline payment -> deterministic checks (Java) -> risk assessment (this service) -> ACCEPT / FLAG / REJECT -> settlement
```

## Setup

```bash
cd ml_service
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
```

Python 3.10+. Tested on 3.12 with scikit-learn 1.8, pandas 3.0, numpy 2.4.

## Run order

| Step | Command | Output |
|---|---|---|
| 1 | `python scripts/01_generate_data.py` | `data/raw.csv.gz`, `data/users.csv` |
| 2 | `python scripts/02_build_features.py` | `data/features.csv.gz` (features, rule flags, user-level split) |
| 3 | `python scripts/03_validate_data.py` | `reports/dataset_report.md`; exits non-zero if a check fails |
| 4 | `python scripts/04_train.py` | `models/` (deploy bundles, thresholds) |
| 5 | `python scripts/05_evaluate.py` | `reports/*.csv`, `evaluation_summary.json` |
| 6 | `python scripts/06_make_figures.py` | `figures/*.pdf` and `*.png` |
| 7 | `python scripts/07_results_tables.py` | `reports/results.md` |

`python scripts/run_all.py` runs all seven. Step 5 includes the unseen-scenario experiment, which retrains every
model once per scenario (about 20 to 30 minutes in total). Use `--skip-loso` to skip it, or
`--loso-only --tiers extended --loso-scenarios rollback,combined` to run part of it; results are cached in `reports/loso_parts/`.

Settings are in `configs/default.yaml` (any field in `offset_ml/config.py` can be overridden). Seeds are fixed
for the generator (42), the user split (7) and the models (13).

## Tests

```bash
pytest
```

26 tests cover state/feature formulas, leakage (features unchanged by later events), rules, generator invariants and
determinism, threshold selection against brute force, and the API (including online/batch feature parity).

## Serving

```bash
uvicorn --factory offset_ml.service.app:create_app --port 8000
```

Run a single worker: per-user behavioural state is held in memory and is lost on restart.
Environment variables: `OFFSET_ML_MODEL_DIR`, `OFFSET_ML_MEDIUM_THRESHOLD`, `OFFSET_ML_HIGH_THRESHOLD`, `OFFSET_ML_CONFIG`.
Models are loaded once and never retrained at inference.

`POST /v1/assess` (the `device` block is optional; without it the native-feature model is used):

```json
{"sender_vpa": "alice@demo", "receiver_vpa": "shop@demo", "amount": 120, "signed_at_ms": 1760000000000,
 "server_balance": 3000, "server_version": 4, "packet_hash": "h1", "nonce": "n1",
 "device": {"device_id": "d", "local_seq": 1, "local_pre_balance": 3000, "snapshot_version": 4, "last_sync_at_ms": 1759999000000}}
```
```json
{"risk_score": 0.009, "risk_level": "LOW", "action": "ACCEPT", "model_version": "offset-extended-random_forest-b13ecc7f",
 "feature_tier": "extended", "policy_violations": []}
```

`action` is REJECT if a deterministic rule fired, FLAG if the level is MEDIUM or HIGH (configurable), otherwise ACCEPT.

## Java integration

Changes under `Offline_UPI-main/src/main/java/com/demo/upimesh/`:

- `model/PaymentInstruction`: optional `deviceId, localSeq, localPreBalance, snapshotVersion, lastSyncAt`.
- `service/DemoService`: simulated phones fill those fields and keep a local balance and counter.
- `service/MlRiskClient` (new): HTTP client, fail-open, timeout 800 ms.
- `service/BridgeIngestionService`: calls the risk service after the existing checks. REJECT is recorded as `REJECTED`,
  FLAG as the new `FLAGGED` status (no funds move), ACCEPT continues to settlement.
- `model/Transaction`: new `FLAGGED` status and `riskScore`, `riskLevel`, `decisionNote` columns.

Enable it in `application.properties`: `upi.ml.enabled=true`, `upi.ml.base-url=http://localhost:8000`.
It is disabled by default, so the existing demo behaves as before.

**These Java changes were not compiled or run** (no JDK in the environment where they were written). Run `mvn -q compile`
and a manual `/api/demo/send` + `/api/mesh/flush` check before relying on them.

## Layout

```
offset_ml/  config, events, state, rules, features, pipeline, split, models, thresholds, metrics,
            training, evaluate, figures, persistence, results; data/ (generator, scenarios, ledger, validate); service/ (app, scoring)
scripts/    numbered entry points     tests/    pytest suite     docs/METHODOLOGY.md   paper-oriented method notes
```

See `docs/METHODOLOGY.md` for the method, formulas, results summary and limitations.
