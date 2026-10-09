"""FastAPI inference service. Run: uvicorn --factory offset_ml.service.app:create_app --port 8000"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from ..config import ROOT, Config, load_config
from ..events import DeviceInfo, TxEvent
from ..logging_utils import get_logger
from .schemas import AssessRequest, AssessResponse
from .scoring import Scorer

log = get_logger("api")


def _env_float(name: str) -> float | None:
    raw = os.environ.get(name)
    return float(raw) if raw else None


def to_event(req: AssessRequest) -> TxEvent:
    dev = req.device
    device = DeviceInfo(dev.device_id, dev.local_seq, dev.local_pre_balance, dev.snapshot_version,
                        dev.last_sync_at_ms / 1000.0) if dev else None
    sync_ms = req.settled_at_ms if req.settled_at_ms is not None else int(time.time() * 1000)
    return TxEvent(req.sender_vpa, req.receiver_vpa, req.amount, req.signed_at_ms / 1000.0, sync_ms / 1000.0,
                   req.packet_hash, req.nonce, req.server_balance, req.server_version, device)


def create_app(scorer: Scorer | None = None, cfg: Config | None = None) -> FastAPI:
    cfg = cfg or load_config(os.environ.get("OFFSET_ML_CONFIG"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if scorer is not None:
            app.state.scorer = scorer
        else:
            model_dir = Path(os.environ.get("OFFSET_ML_MODEL_DIR", ROOT / "models"))
            try:
                app.state.scorer = Scorer.from_dir(model_dir, cfg, _env_float("OFFSET_ML_MEDIUM_THRESHOLD"),
                                                   _env_float("OFFSET_ML_HIGH_THRESHOLD"))
                log.info("loaded models from %s", model_dir)
            except (FileNotFoundError, RuntimeError) as exc:
                log.error("model load failed: %s", exc)
                app.state.scorer = None
        yield

    app = FastAPI(title="OffSet behavioural risk service", version="1.0.0", lifespan=lifespan)

    def get_scorer() -> Scorer:
        s = app.state.scorer
        if s is None:
            raise HTTPException(status_code=503, detail="model bundle not loaded")
        return s

    @app.get("/health")
    def health() -> dict:
        s = app.state.scorer
        return {"status": "ok" if s else "degraded", "model_loaded": s is not None}

    @app.get("/v1/model")
    def model_info() -> dict:
        s = get_scorer()
        return {tier: {"model_version": meta["model_version"], "model": meta["model_name"],
                       "thresholds": {"medium": s.medium if s.medium is not None else meta["thresholds"]["medium"],
                                      "high": s.high if s.high is not None else meta["thresholds"]["high"]},
                       "n_features": len(meta["features"])}
                for tier, (_, meta) in s.bundles.items()}

    @app.post("/v1/assess", response_model=AssessResponse)
    def assess(req: AssessRequest) -> AssessResponse:
        s = get_scorer()
        try:
            result = s.assess(to_event(req))
        except Exception as exc:  # never let a scoring error take down payment ingestion
            log.exception("assessment failed")
            raise HTTPException(status_code=500, detail=f"assessment failed: {type(exc).__name__}") from exc
        return AssessResponse(risk_score=result.risk_score, risk_level=result.risk_level, action=result.action,
                              model_version=result.model_version, feature_tier=result.feature_tier,
                              policy_violations=result.policy_violations)

    return app
