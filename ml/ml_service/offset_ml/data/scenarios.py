"""Explicit fraud scenarios. Each returns a list of event dicts (or None if not applicable).

Attack transactions are appended after the episode's legitimate ones, so local-state chains stay ordered.
Location-based scenarios are omitted: OffSet carries no location data.
"""
from __future__ import annotations

import numpy as np


def _round(x: float) -> float:
    step = 5 if x < 100 else 10 if x < 500 else 50
    return float(max(5.0, round(x / step) * step))


def _meta(name: str, variant: str, label: int = 1) -> dict:
    return {"label": label, "scenario": name if label else "", "variant": variant}


def _times(start: float, gaps) -> list[float]:
    return list(start + np.concatenate([[0.0], np.cumsum(gaps[:-1])])) if len(gaps) else []


def _headroom(sim, ep, ts: float) -> float:
    return max(0.0, sim.pol.daily_limit - sim.settled_day_spend(ts) - sum(e["amount"] for e in ep.legit))


def _receivers(sim, n: int, new_prob: float) -> list[str]:
    return [sim.new_receiver() if sim.rng.random() < new_prob else sim.known_receiver() for _ in range(n)]


def large_amount(sim, ep):
    m, rng = sim.p.amount_median, sim.rng
    cap = min(sim.pol.max_amount, ep.local)
    if 4 * m > 0.95 * cap:
        return None
    amount = min(_round(m * rng.uniform(6, 20)), np.floor(0.95 * cap))
    if amount < 4 * m:
        return None
    new = rng.random() < 0.3
    t = ep.place(60, rng)
    return sim.chain(ep, [t], _receivers(sim, 1, 1.0 if new else 0.0), [amount],
                     **_meta("large_amount", "new_receiver" if new else "known_receiver"))


def new_beneficiary_unusual_amount(sim, ep):
    m, rng = sim.p.amount_median, sim.rng
    cap = min(sim.pol.max_amount, ep.local)
    if 3 * m > 0.95 * cap:
        return None
    n = int(rng.integers(1, 3))
    amounts = [min(_round(m * rng.uniform(3, 8)), np.floor(0.95 * cap)) for _ in range(n)]
    t0 = ep.place(900 * n, rng)
    times = _times(t0, rng.uniform(60, 900, n))
    return sim.chain(ep, times, _receivers(sim, n, 1.0), amounts, **_meta("new_beneficiary_unusual_amount", f"n{n}"))


def device_change(sim, ep):
    m, rng = sim.p.amount_median, sim.rng
    cap = min(sim.pol.max_amount, ep.local)
    n = int(rng.integers(1, 4))
    amounts = [min(_round(m * rng.uniform(1.5, 4)), np.floor(cap)) for _ in range(n)]
    t0 = ep.place(1200 * n, rng)
    times = _times(t0, rng.uniform(60, 1200, n))
    return sim.chain(ep, times, _receivers(sim, n, 0.6), amounts, device_id=sim.new_device(),
                     **_meta("device_change", f"n{n}"))


def velocity_burst(sim, ep):
    m, rng = sim.p.amount_median, sim.rng
    blatant = rng.random() < 0.5
    n = int(rng.integers(12, 27)) if blatant else int(rng.integers(6, 10))
    gaps = rng.uniform(15, 100, n) if blatant else rng.uniform(120, 480, n)
    t0 = ep.place(float(gaps.sum()), rng)
    amounts = np.array([_round(m * rng.uniform(0.8, 2.0)) for _ in range(n)])
    budget = 0.9 * ep.local if blatant else min(0.9 * ep.local, _headroom(sim, ep, t0))
    if amounts.sum() > budget:
        amounts = np.maximum(5.0, np.floor(amounts * budget / amounts.sum() / 5) * 5)
    pool = _receivers(sim, int(rng.integers(1, 4)), 0.5)
    receivers = [pool[int(rng.integers(len(pool)))] for _ in range(n)]
    return sim.chain(ep, _times(t0, gaps), receivers, amounts,
                     **_meta("velocity_burst", "blatant" if blatant else "evasive"))


def cumulative_offline_spend(sim, ep):
    m, rng = sim.p.amount_median, sim.rng
    heavy = rng.random() < 0.5
    n = int(rng.integers(12, 21)) if heavy else int(rng.integers(8, 17))
    gaps = rng.uniform(240, 1200, n)
    t0 = ep.place(float(gaps.sum()), rng)
    if heavy:
        amounts = [max(_round(m * rng.uniform(1.5, 3)), sim.pol.daily_limit / n * rng.uniform(1.0, 1.3)) for _ in range(n)]
    else:
        amounts = [_round(m * rng.uniform(1, 2.5)) for _ in range(n)]
        budget = min(0.9 * ep.local, _headroom(sim, ep, t0))
        if sum(amounts) > budget:
            amounts = [max(5.0, np.floor(a * budget / sum(amounts) / 5) * 5) for a in amounts]
    return sim.chain(ep, _times(t0, gaps), _receivers(sim, n, 0.2), amounts,
                     **_meta("cumulative_offline_spend", "heavy" if heavy else "moderate"))


def long_offline_suspicious(sim, ep):
    m, rng = sim.p.amount_median, sim.rng
    over = rng.random() < 0.5
    duration = rng.uniform(12.5, 20) * 3600 if over else rng.uniform(6.5, 11.5) * 3600
    ep.t1 = max(ep.t1, ep.t0 + duration)
    n = int(rng.integers(2, 6))
    gaps = rng.uniform(60, 900, n)
    start = max(ep.t0 + duration * rng.uniform(0.8, 0.98), ep.last_signed + 30)
    ep.t1 = max(ep.t1, start + float(gaps.sum()) + 60)
    amounts = [min(_round(m * rng.uniform(2, 5)), np.floor(min(sim.pol.max_amount, ep.local))) for _ in range(n)]
    return sim.chain(ep, _times(start, gaps), _receivers(sim, n, 0.5), amounts,
                     **_meta("long_offline_suspicious", "over_limit" if over else "under_limit"))


def rollback(sim, ep):
    m, rng = sim.p.amount_median, sim.rng
    older = [s for s in sim.snapshots if s[0] < ep.snap_v and abs(s[1] - ep.local) > 1]
    restore = bool(older) and rng.random() < 0.5
    n = int(rng.integers(1, 3))
    t0 = ep.place(600 * n, rng)
    times = _times(t0, rng.uniform(60, 600, n))
    amounts = [_round(m * rng.uniform(1, 3)) for _ in range(n)]
    receivers = _receivers(sim, n, 0.3)
    if restore:
        version, balance, seq = older[-1]
        keep_counter = rng.random() < 0.5
        if not keep_counter:
            ep.seq = seq
        out = sim.chain(ep, times, receivers, amounts, pre_override=balance, snap_v=version,
                        **_meta("rollback", "restore_old_counter" if not keep_counter else "restore_snapshot"))
    else:
        inflate = ep.local + rng.uniform(0.2, 1.0) * ep.snap_b
        out = sim.chain(ep, times, receivers, amounts, pre_override=round(inflate, 2),
                        **_meta("rollback", "inflated_balance"))
    return out


def double_spend(sim, ep):
    rng, b = sim.rng, ep.local
    if b > 1.9 * sim.pol.max_amount or b < 300:
        return None
    a1 = min(sim.pol.max_amount, float(_round(rng.uniform(0.55, 0.8) * b)))
    left = b - a1
    a2 = min(sim.pol.max_amount, float(_round(left + rng.uniform(0.1, 0.4) * b)))
    if a2 <= left or a2 > b or a1 > b:
        return None
    t0 = ep.place(700, rng)
    gap = float(rng.uniform(30, 600))
    first = sim.chain(ep, [t0], _receivers(sim, 1, 0.5), [a1], **_meta("double_spend", "first_leg", label=0))
    if not first:
        return None
    a = first[0]
    same_seq = rng.random() < 0.5
    second = sim.event(ep, t0 + gap, sim.new_receiver(), a2, a["local_pre_balance"],
                       a["local_seq"] if same_seq else a["local_seq"] + 1,
                       **_meta("double_spend", "same_sequence" if same_seq else "stale_balance"))
    ep.seq = max(ep.seq, second["local_seq"])
    return first + [second]


def replay_duplicate(sim, ep):
    rng = sim.rng
    variants = []
    if ep.legit:
        variants += ["exact_duplicate", "nonce_reuse"]
    old = [r for r in sim.rows if r["outcome"] == "SETTLED" and r["fraud_label"] == 0
           and r["sync_at"] < ep.t0 - 25 * 3600]
    if old:
        variants.append("stale_replay")
    if not variants:
        return None
    variant = variants[int(rng.integers(len(variants)))]
    meta = {"fraud_label": 1, "fraud_scenario": "replay_duplicate", "fraud_variant": variant}
    if variant == "stale_replay":
        return [sim.clone(old[int(rng.integers(len(old)))], **meta)]
    orig = ep.legit[int(rng.integers(len(ep.legit)))]
    if variant == "exact_duplicate":
        return [sim.clone(orig, _dup_of=orig, _dup_delay=float(rng.uniform(120, 4 * 3600)), **meta)]
    salt = f"{int(rng.integers(2 ** 40)):x}"
    packet = sim.event(ep, orig["signed_at"] + rng.uniform(30, 600), orig["receiver_id"], orig["amount"],
                       orig["local_pre_balance"], orig["local_seq"])
    packet.update(nonce=orig["nonce"], packet_hash=packet["packet_hash"][:12] + salt[:12], **meta)
    ep.last_signed = max(ep.last_signed, packet["signed_at"])
    ep.t1 = max(ep.t1, packet["signed_at"] + 60)
    return [packet]


def combined(sim, ep):
    m, rng = sim.p.amount_median, sim.rng
    signals = [str(s) for s in rng.choice(
        ["new_device", "new_receiver", "large_amount", "burst", "long_offline", "rollback"],
        size=int(rng.integers(3, 5)), replace=False)]
    n = int(rng.integers(2, 5))
    gaps = rng.uniform(20, 90, n) if "burst" in signals else rng.uniform(300, 1500, n)
    if "long_offline" in signals:
        duration = rng.uniform(6, 11.5) * 3600
        ep.t1 = max(ep.t1, ep.t0 + duration)
        start = max(ep.t0 + duration * rng.uniform(0.8, 0.98), ep.last_signed + 30)
        ep.t1 = max(ep.t1, start + float(gaps.sum()) + 60)
    else:
        start = ep.place(float(gaps.sum()), rng)
    lo, hi = (4, 12) if "large_amount" in signals else (1.5, 4)
    cap = min(sim.pol.max_amount, ep.local)
    if m * lo > 0.95 * cap:
        return None
    amounts = [min(_round(m * rng.uniform(lo, hi)), np.floor(0.95 * cap)) for _ in range(n)]
    pre = round(ep.local + rng.uniform(0.2, 1.0) * ep.snap_b, 2) if "rollback" in signals else None
    return sim.chain(ep, _times(start, gaps), _receivers(sim, n, 1.0 if "new_receiver" in signals else 0.2), amounts,
                     pre_override=pre, device_id=sim.new_device() if "new_device" in signals else None,
                     **_meta("combined", "+".join(sorted(signals))))


SCENARIOS = {
    "rollback": rollback,
    "double_spend": double_spend,
    "velocity_burst": velocity_burst,
    "large_amount": large_amount,
    "new_beneficiary_unusual_amount": new_beneficiary_unusual_amount,
    "device_change": device_change,
    "long_offline_suspicious": long_offline_suspicious,
    "cumulative_offline_spend": cumulative_offline_spend,
    "replay_duplicate": replay_duplicate,
    "combined": combined,
}
