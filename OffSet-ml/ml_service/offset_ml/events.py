"""Event representation shared by the generator, batch feature pipeline and inference service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DeviceInfo:
    """Fields the sender's phone would add to PaymentInstruction (proposed protocol extension)."""
    device_id: str
    local_seq: int
    local_pre_balance: float
    snapshot_version: int
    last_sync_at: float


@dataclass(frozen=True)
class TxEvent:
    """One payment as seen by the backend at synchronisation time. Times are epoch seconds."""
    user_id: str
    receiver_id: str
    amount: float
    signed_at: float
    sync_at: float
    packet_hash: str
    nonce: str
    server_balance: float
    server_version: int
    device: Optional[DeviceInfo] = None

    def without_device(self) -> "TxEvent":
        return TxEvent(self.user_id, self.receiver_id, self.amount, self.signed_at, self.sync_at,
                       self.packet_hash, self.nonce, self.server_balance, self.server_version, None)
