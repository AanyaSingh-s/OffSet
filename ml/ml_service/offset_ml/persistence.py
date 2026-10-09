from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import sklearn


def model_version(name: str, tier: str, features: list[str], seed: int) -> str:
    digest = hashlib.sha1(json.dumps([name, tier, features, seed]).encode()).hexdigest()[:8]
    return f"offset-{tier}-{name}-{digest}"


def save_bundle(path: Path, model, meta: dict) -> None:
    meta = {**meta, "sklearn_version": sklearn.__version__}
    joblib.dump({"model": model, "meta": meta}, path, compress=3)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2))


def load_bundle(path: Path) -> tuple[object, dict]:
    obj = joblib.load(path)
    if obj["meta"].get("sklearn_version") != sklearn.__version__:
        raise RuntimeError(
            f"{path.name} was trained with scikit-learn {obj['meta'].get('sklearn_version')}, "
            f"installed {sklearn.__version__}; retrain with scripts/04_train.py")
    return obj["model"], obj["meta"]
