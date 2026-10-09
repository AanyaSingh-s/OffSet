"""Typed configuration. Defaults live here; configs/default.yaml may override any field."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class PolicyConfig:
    """Deterministic limits. 'Native' rules mirror the Java backend; the rest are proposed policy."""
    packet_max_age_s: int = 86400        # upi.mesh.packet-max-age-seconds
    idempotency_ttl_s: int = 86400       # upi.mesh.idempotency-ttl-seconds
    future_skew_s: int = 300             # BridgeIngestionService clock-skew tolerance
    max_amount: float = 1000.0           # proposed per-transaction limit (INR)
    daily_limit: float = 2500.0          # proposed cumulative offline limit per IST day (INR)
    max_tx_per_hour: int = 10            # proposed velocity limit
    max_offline_hours: float = 12.0      # proposed offline-duration limit
    balance_tol: float = 0.01


@dataclass
class GeneratorConfig:
    seed: int = 42
    n_users: int = 3000
    horizon_days: int = 180
    start_date: str = "2025-01-01"
    tz_offset_s: int = 19800             # IST
    outage_rate_per_day: float = 0.4
    outage_median_min: float = 45.0
    outage_sigma: float = 1.0
    outage_max_hours: float = 11.0
    late_sync_prob: float = 0.08
    late_sync_median_h: float = 4.0
    late_sync_sigma: float = 1.0
    late_sync_max_h: float = 40.0
    external_debit_prob: float = 0.015   # other-channel debit during an outage (legitimate)
    legit_device_change_prob: float = 0.01
    legit_cluster_prob: float = 0.03     # legitimate bursts, e.g. a group meal
    legit_large_prob: float = 0.02
    legit_new_receiver_prob: float = 0.07
    attack_episode_prob: float = 0.009


@dataclass
class FeatureConfig:
    min_history: int = 5
    std_floor: float = 0.1
    z_clip: float = 10.0
    prior_strength: float = 3.0
    interval_cap_s: float = 604800.0


@dataclass
class SplitConfig:
    seed: int = 7
    train: float = 0.6
    val: float = 0.2


@dataclass
class ModelConfig:
    seed: int = 13
    rf_trees: int = 300
    rf_min_leaf: int = 5
    if_trees: int = 300
    if_max_samples: int = 256
    lr_c: float = 1.0
    loso_rf_trees: int = 150
    f_beta: float = 2.0
    max_fpr: float = 0.03
    high_precision: float = 0.90


@dataclass
class ServiceConfig:
    flag_levels: list[str] = field(default_factory=lambda: ["MEDIUM", "HIGH"])


@dataclass
class Config:
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    split: SplitConfig = field(default_factory=SplitConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    service: ServiceConfig = field(default_factory=ServiceConfig)


def _merge(obj: Any, values: dict[str, Any]) -> None:
    valid = {f.name for f in dataclasses.fields(obj)}
    for key, val in values.items():
        if key not in valid:
            raise ValueError(f"Unknown config key '{key}' for {type(obj).__name__}")
        current = getattr(obj, key)
        if dataclasses.is_dataclass(current):
            _merge(current, val)
        else:
            setattr(obj, key, val)


def load_config(path: str | Path | None = None) -> Config:
    cfg = Config()
    path = Path(path) if path else ROOT / "configs" / "default.yaml"
    if path.exists():
        _merge(cfg, yaml.safe_load(path.read_text()) or {})
    return cfg


def _ensure(name: str) -> Path:
    p = ROOT / name
    p.mkdir(exist_ok=True)
    return p


def data_dir() -> Path:
    return _ensure("data")


def models_dir() -> Path:
    return _ensure("models")


def reports_dir() -> Path:
    return _ensure("reports")


def figures_dir() -> Path:
    return _ensure("figures")
