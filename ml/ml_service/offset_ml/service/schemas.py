from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DevicePayload(BaseModel):
    device_id: str = Field(min_length=1)
    local_seq: int = Field(ge=0)
    local_pre_balance: float = Field(ge=0)
    snapshot_version: int = Field(ge=0)
    last_sync_at_ms: int = Field(ge=0)


class AssessRequest(BaseModel):
    transaction_id: Optional[str] = None
    sender_vpa: str = Field(min_length=1)
    receiver_vpa: str = Field(min_length=1)
    amount: float = Field(gt=0)
    signed_at_ms: int = Field(ge=0)
    settled_at_ms: Optional[int] = Field(default=None, ge=0, description="Defaults to server time")
    server_balance: float = Field(ge=0, description="Sender balance before settlement")
    server_version: int = Field(default=0, ge=0)
    packet_hash: str = Field(min_length=1)
    nonce: str = Field(min_length=1)
    device: Optional[DevicePayload] = None


class AssessResponse(BaseModel):
    risk_score: float
    risk_level: str
    action: str
    model_version: str
    feature_tier: str
    policy_violations: list[str]
