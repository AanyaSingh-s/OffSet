"""Stateful synthetic generator: persistent user profiles, device/ledger state, outage episodes."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..config import Config
from ..logging_utils import get_logger
from ..state import local_time_parts
from .ledger import ServerLedger
from .profiles import UserProfile, sample_profile, user_id
from .scenarios import SCENARIOS

log = get_logger("generator")


def round_amount(x: float) -> float:
    step = 5 if x < 100 else 10 if x < 500 else 50
    return float(max(5.0, round(x / step) * step))


@dataclass
class Episode:
    t0: float
    t1: float
    last_sync: float
    snap_v: int
    snap_b: float
    local: float
    seq: int
    device_id: str
    last_signed: float = 0.0
    legit: list = field(default_factory=list)
    attack: list = field(default_factory=list)

    def place(self, span: float, rng: np.random.Generator) -> float:
        """Pick a start time after the last transaction; extend the outage if the span does not fit."""
        lo = max(self.t0, self.last_signed + 30)
        hi = max(lo, self.t1 - span)
        start = float(rng.uniform(lo, hi))
        self.t1 = max(self.t1, start + span + 60)
        return start


class Shared:
    """State shared across users: id pools and attack bookkeeping."""

    def __init__(self, merchants: list[str]):
        self.merchants = merchants
        self.scenario_counts = {k: 0 for k in SCENARIOS}
        self.attack_id = 0


class UserSim:
    def __init__(self, prof: UserProfile, cfg: Config, rng: np.random.Generator, shared: Shared):
        self.p, self.cfg, self.g, self.pol = prof, cfg, cfg.generator, cfg.policy
        self.rng, self.shared = rng, shared
        self.ledger = ServerLedger(prof.target_balance, cfg.policy)
        self.device_id = f"{prof.user_id}-d0"
        self.n_devices = 1
        self.seq = 0
        self.used: set[str] = set()
        self.last_pay: tuple[str, float] | None = None
        self.snapshots: list[tuple[int, float, int]] = []
        self.rows: list[dict] = []
        self.day_spent: dict[int, float] = {}
        self.arrival = 0

    # ---- sampling helpers -------------------------------------------------
    def activity(self, ts: float) -> float:
        hour, _, weekend = local_time_parts(ts, self.g.tz_offset_s)
        circ = math.exp(self.p.kappa * (math.cos(2 * math.pi * (hour - self.p.peak_hour) / 24) - 1))
        return circ * (self.p.weekend_factor if weekend else self.p.weekday_factor)

    def amount(self) -> float:
        x = self.p.amount_median * self.rng.lognormal(0, self.p.amount_sigma)
        return min(round_amount(x), self.pol.max_amount)

    def known_receiver(self) -> str:
        return str(self.rng.choice(self.p.favourites, p=self.p.favourite_weights))

    def new_receiver(self) -> str:
        pool = self.shared.merchants
        for _ in range(50):
            r = str(self.rng.choice(pool))
            if r not in self.used and r not in self.p.favourites:
                return r
        return str(self.rng.choice(pool))

    def new_device(self) -> str:
        self.n_devices += 1
        return f"{self.p.user_id}-d{self.n_devices - 1}"

    def settled_day_spend(self, ts: float) -> float:
        _, day, _ = local_time_parts(ts, self.g.tz_offset_s)
        return self.day_spent.get(day, 0.0)

    def event(self, ep: Episode, signed: float, receiver: str, amount: float, pre: float, seq: int, *,
              device_id: str | None = None, snap_v: int | None = None, label: int = 0,
              scenario: str = "", variant: str = "", attack_id: int = 0) -> dict:
        nonce = f"{int(self.rng.integers(2 ** 62)):016x}"
        signed = int(round(signed))
        h = hashlib.sha256(f"{nonce}|{receiver}|{amount}|{signed}|{seq}".encode()).hexdigest()[:24]
        return {
            "user_id": self.p.user_id, "receiver_id": receiver, "amount": round(float(amount), 2),
            "signed_at": signed, "nonce": nonce, "packet_hash": h,
            "device_id": device_id or ep.device_id, "local_seq": int(seq),
            "local_pre_balance": round(float(pre), 2), "local_post_balance": round(float(pre) - float(amount), 2),
            "snapshot_version": ep.snap_v if snap_v is None else int(snap_v),
            "last_sync_at": int(round(ep.last_sync)), "last_synced_server_balance": ep.snap_b,
            "fraud_label": label, "fraud_scenario": scenario, "fraud_variant": variant, "attack_id": attack_id,
        }

    def clone(self, orig: dict, **over) -> dict:
        drop = ("sync_at", "server_balance_before", "server_version_before", "outcome", "reject_reason", "arrival_idx")
        c = {k: v for k, v in orig.items() if k not in drop}
        c.update(over)
        return c

    def chain(self, ep: Episode, times, receivers, amounts, *, pre_override: float | None = None,
              device_id: str | None = None, **meta) -> list[dict]:
        """Consecutive transactions on one local balance chain; amounts are capped by the local balance."""
        out, bal = [], ep.local if pre_override is None else pre_override
        for i, (t, r, a) in enumerate(zip(times, receivers, amounts)):
            a = min(float(a), self.pol.max_amount, math.floor(bal))
            if a < 5:
                break
            ep.seq += 1
            out.append(self.event(ep, t, r, a, bal, ep.seq, device_id=device_id, **meta))
            bal = round(bal - a, 2)
            ep.last_signed = max(ep.last_signed, t)
        if out:
            ep.local = bal
        return out

    # ---- legitimate behaviour ---------------------------------------------
    def _legit_times(self, ep: Episode) -> list[float]:
        dur_h = (ep.t1 - ep.t0) / 3600
        cand = np.sort(self.rng.uniform(ep.t0, ep.t1, self.rng.poisson(self.p.rate_per_hour * dur_h)))
        times = [float(t) for t in cand if self.rng.random() < self.activity(t)]
        if self.p.archetype in ("frequent_low", "merchant_heavy") and self.rng.random() < self.g.legit_cluster_prob:
            t = float(self.rng.uniform(ep.t0, ep.t1))
            for _ in range(int(self.rng.integers(3, 7))):
                t += float(self.rng.uniform(60, 360))
                times.append(t)
            ep.t1 = max(ep.t1, t + 60)
        return sorted(times)

    def _legit_txs(self, ep: Episode) -> None:
        planned: dict[int, float] = {}
        recent: list[float] = []
        for t in self._legit_times(ep):
            if self.last_pay and self.rng.random() < self.p.repeat_prob:
                receiver, amount = self.last_pay
            else:
                is_new = self.rng.random() < self.g.legit_new_receiver_prob
                receiver = self.new_receiver() if is_new else self.known_receiver()
                amount = self.amount()
                if self.rng.random() < self.g.legit_large_prob:
                    amount = min(round_amount(self.p.amount_median * self.rng.uniform(3, 7)), self.pol.max_amount)
            _, day, _ = local_time_parts(t, self.g.tz_offset_s)
            day_total = self.day_spent.get(day, 0.0) + planned.get(day, 0.0)
            recent = [x for x in recent if x > t - 3600]
            if (amount > ep.local or day_total + amount > self.pol.daily_limit
                    or len(recent) >= self.pol.max_tx_per_hour - 1):
                continue
            ev = self.chain(ep, [t], [receiver], [amount])
            if not ev:
                continue
            ep.legit.extend(ev)
            planned[day] = planned.get(day, 0.0) + amount
            recent.append(t)
            self.used.add(receiver)
            self.last_pay = (receiver, amount)

    # ---- episode lifecycle --------------------------------------------------
    def _online_credits(self) -> None:
        target = self.p.target_balance
        if self.ledger.balance < 0.8 * target:
            self.ledger.credit(round(target * self.rng.uniform(0.8, 1.1) - self.ledger.balance, 2))
        elif self.rng.random() < 0.1:
            self.ledger.credit(round(target * self.rng.uniform(0.05, 0.3), 2))

    def _pick_attack(self, ep: Episode) -> list[dict] | None:
        counts = self.shared.scenario_counts
        names = list(SCENARIOS)
        w = np.array([1.0 / (1 + counts[n]) for n in names])
        order = self.rng.choice(len(names), size=len(names), replace=False, p=w / w.sum())
        for i in order:
            name = names[i]
            events = SCENARIOS[name](self, ep)
            if events:
                self.shared.attack_id += 1
                for e in events:
                    if e["fraud_label"]:
                        e["attack_id"] = self.shared.attack_id
                counts[name] += 1
                return events
        return None

    def episode(self, prev_end: float, t0: float) -> float:
        g, rng = self.g, self.rng
        dur = float(np.clip(rng.lognormal(math.log(g.outage_median_min * 60), g.outage_sigma),
                            600, g.outage_max_hours * 3600))
        last_sync = max(prev_end, t0 - float(rng.uniform(0, 1200)))
        self._online_credits()
        ep = Episode(t0, t0 + dur, last_sync, self.ledger.version, self.ledger.balance,
                     self.ledger.balance, self.seq, self.device_id)
        self.snapshots = (self.snapshots + [(ep.snap_v, ep.snap_b, ep.seq)])[-6:]
        if rng.random() < g.legit_device_change_prob:
            self.device_id = ep.device_id = self.new_device()
        self._legit_txs(ep)
        if rng.random() < g.attack_episode_prob:
            ep.attack = self._pick_attack(ep) or []
        self.seq = max([self.seq] + [e["local_seq"] for e in ep.legit + ep.attack])

        if rng.random() < g.external_debit_prob and self.ledger.balance > 100:
            self.ledger.debit_external(round(self.ledger.balance * rng.uniform(0.3, 0.8), 2))

        connect = float(np.clip(rng.lognormal(math.log(120), 0.8), 30, 1800))
        sync_start = ep.t1 + connect
        if rng.random() < g.late_sync_prob:
            sync_start += float(np.clip(rng.lognormal(math.log(g.late_sync_median_h * 3600), g.late_sync_sigma),
                                        0, g.late_sync_max_h * 3600))
        return self._sync(ep, sync_start)

    def _sync(self, ep: Episode, start: float) -> float:
        batch = ep.legit + ep.attack
        t = start
        for e in batch:
            if "_dup_of" not in e:
                t += float(self.rng.uniform(1, 4))
                e["sync_at"] = int(round(t))
        for e in batch:
            if "_dup_of" in e:
                e["sync_at"] = int(e.pop("_dup_of")["sync_at"] + e.pop("_dup_delay"))
        for e in sorted(batch, key=lambda r: r["sync_at"]):
            res = self.ledger.settle(e)
            e.update(res)
            e["arrival_idx"] = self.arrival
            self.arrival += 1
            if res["outcome"] == "SETTLED":
                _, day, _ = local_time_parts(e["signed_at"], self.g.tz_offset_s)
                self.day_spent[day] = self.day_spent.get(day, 0.0) + e["amount"]
            self.rows.append(e)
        return float(max([start] + [e["sync_at"] for e in batch]))

    def run(self, t_start: float, t_end: float) -> None:
        t = t_start
        while True:
            t0 = t + float(self.rng.exponential(86400 / self.p.outage_rate))
            if t0 >= t_end:
                break
            t = self.episode(t, t0)


def generate(cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    g = cfg.generator
    start = datetime.fromisoformat(g.start_date).replace(tzinfo=timezone.utc).timestamp() - g.tz_offset_s
    end = start + g.horizon_days * 86400
    seeds = np.random.SeedSequence(g.seed).spawn(g.n_users)
    merchants = [f"m{j:04d}@merchant" for j in range(2000)]
    ids = [user_id(i) for i in range(g.n_users)]
    shared = Shared(merchants)

    rows, profiles = [], []
    for i in range(g.n_users):
        rng = np.random.default_rng(seeds[i])
        prof = sample_profile(rng, i, g, merchants, ids)
        sim = UserSim(prof, cfg, rng, shared)
        sim.run(start, end)
        rows.extend(sim.rows)
        profiles.append(prof.to_row())

    df = pd.DataFrame(rows).sort_values(["user_id", "arrival_idx"], kind="stable").reset_index(drop=True)
    df.insert(0, "tx_id", [f"T{i:08d}" for i in range(len(df))])
    df["sync_lag_min"] = (df["sync_at"] - df["signed_at"]) / 60.0
    df["is_weekend_signed"] = [local_time_parts(t, g.tz_offset_s)[2] for t in df["signed_at"]]
    log.info("generated %d transactions for %d users (%d fraud, %.2f%%)", len(df), g.n_users,
             df.fraud_label.sum(), 100 * df.fraud_label.mean())
    return df, pd.DataFrame(profiles)
