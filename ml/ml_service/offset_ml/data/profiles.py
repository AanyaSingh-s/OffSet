"""Persistent behavioural profiles for synthetic users."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from ..config import GeneratorConfig

# name: (peak tx rate per outage-hour, median amount, log-sigma, merchant share, n favourites, repeat prob, weight)
ARCHETYPES = {
    "frequent_low": (3.0, 50.0, 0.5, 0.85, 6, 0.35, 0.30),
    "occasional": (1.0, 150.0, 0.6, 0.60, 4, 0.15, 0.25),
    "larger_payment": (0.9, 350.0, 0.5, 0.60, 5, 0.10, 0.15),
    "merchant_heavy": (2.2, 90.0, 0.5, 0.97, 8, 0.30, 0.15),
    "transfer_heavy": (1.4, 220.0, 0.6, 0.20, 5, 0.20, 0.15),
}
PEAK_HOURS = (9.0, 13.0, 19.0, 22.0)


@dataclass
class UserProfile:
    user_id: str
    archetype: str
    rate_per_hour: float
    amount_median: float
    amount_sigma: float
    merchant_share: float
    repeat_prob: float
    outage_rate: float
    peak_hour: float
    kappa: float
    weekday_factor: float
    weekend_factor: float
    target_balance: float
    favourites: list[str]
    favourite_weights: list[float]

    def to_row(self) -> dict:
        d = asdict(self)
        d["favourites"] = "|".join(self.favourites)
        d.pop("favourite_weights")
        return d


def user_id(idx: int) -> str:
    return f"u{idx:05d}@offset"


def sample_profile(rng: np.random.Generator, idx: int, g: GeneratorConfig,
                   merchants: list[str], user_ids: list[str]) -> UserProfile:
    names = list(ARCHETYPES)
    weights = np.array([ARCHETYPES[k][6] for k in names])
    name = names[rng.choice(len(names), p=weights / weights.sum())]
    rate, med, sig, m_share, n_fav, rep, _ = ARCHETYPES[name]
    uid = user_id(idx)
    n_m = int(round(n_fav * m_share))
    n_p = max(n_fav - n_m, 0) if m_share < 0.95 else 0
    favs = list(rng.choice(merchants, size=max(n_m, 1), replace=False))
    peers = [u for u in user_ids if u != uid]
    if n_p:
        favs += list(rng.choice(peers, size=n_p, replace=False))
    rng.shuffle(favs)
    zipf = 1.0 / np.arange(1, len(favs) + 1)
    quiet = rng.uniform(0.5, 1.0)
    weekend_heavy = rng.random() < 0.5
    return UserProfile(
        user_id=uid, archetype=name,
        rate_per_hour=rate * rng.lognormal(0, 0.2),
        amount_median=med * rng.lognormal(0, 0.2),
        amount_sigma=sig, merchant_share=m_share, repeat_prob=rep,
        outage_rate=g.outage_rate_per_day * rng.lognormal(0, 0.4),
        peak_hour=float(rng.choice(PEAK_HOURS) + rng.normal(0, 1.5)) % 24,
        kappa=float(rng.uniform(0.8, 2.0)),
        weekday_factor=1.0 if weekend_heavy is False else quiet,
        weekend_factor=quiet if weekend_heavy is False else 1.0,
        target_balance=float(np.clip(rng.lognormal(np.log(2000), 0.7), 300, 10000)),
        favourites=[str(f) for f in favs], favourite_weights=list(zipf / zipf.sum()),
    )
