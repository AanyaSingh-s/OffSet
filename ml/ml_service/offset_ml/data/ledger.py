"""Server-side ledger simulation for one account. Settlement uses the backend's native rules only."""
from __future__ import annotations

from ..config import PolicyConfig
from ..events import TxEvent
from ..rules import native_flags


class ServerLedger:
    def __init__(self, balance: float, policy: PolicyConfig):
        self.balance = round(balance, 2)
        self.version = 0
        self.policy = policy
        self.seen_hashes: dict[str, float] = {}

    def credit(self, amount: float) -> None:
        self.balance = round(self.balance + amount, 2)
        self.version += 1

    def debit_external(self, amount: float) -> bool:
        if amount > self.balance:
            return False
        self.balance = round(self.balance - amount, 2)
        self.version += 1
        return True

    def settle(self, row: dict) -> dict:
        """Mirror BridgeIngestionService + SettlementService. The balance never goes negative."""
        ev = TxEvent(row["user_id"], row["receiver_id"], row["amount"], row["signed_at"], row["sync_at"],
                     row["packet_hash"], row["nonce"], self.balance, self.version)
        flags = native_flags(ev, self.seen_hashes.get(ev.packet_hash), self.policy)
        out = {"server_balance_before": self.balance, "server_version_before": self.version,
               "outcome": "SETTLED", "reject_reason": ""}
        if flags["N_DUPLICATE_PACKET"]:
            out.update(outcome="DUPLICATE", reject_reason="N_DUPLICATE_PACKET")
            return out
        self.seen_hashes.setdefault(ev.packet_hash, ev.sync_at)
        for rule in ("N_STALE", "N_FUTURE_DATED", "N_INSUFFICIENT_BALANCE"):
            if flags[rule]:
                out.update(outcome="REJECTED", reject_reason=rule)
                return out
        self.balance = round(self.balance - ev.amount, 2)
        self.version += 1
        return out
