import pytest

from OffSet.ml_service.offset_ml.config import load_config
from OffSet.ml_service.offset_ml.data.generator import generate
from OffSet.ml_service.offset_ml.pipeline import build_features
from OffSet.ml_service.offset_ml.split import add_split


@pytest.fixture(scope="session")
def cfg():
    c = load_config()
    c.generator.n_users = 120
    c.generator.seed = 5
    return c


@pytest.fixture(scope="session")
def small(cfg):
    raw, users = generate(cfg)
    feats = add_split(build_features(raw, users, cfg), users, cfg.split)
    return raw, users, feats
