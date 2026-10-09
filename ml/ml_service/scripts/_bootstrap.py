"""Bootstrap direct script execution from the repository checkout."""
from __future__ import annotations

import importlib.machinery
import sys
import types
from pathlib import Path


def ensure_project_imports() -> None:
    """Expose the checked-out ML package as OffSet.ml_service without installation."""
    repo_root = Path(__file__).resolve().parents[3]
    ml_root = repo_root / "ml"
    if str(ml_root) not in sys.path:
        sys.path.insert(0, str(ml_root))

    pkg = sys.modules.get("OffSet")
    if pkg is None:
        pkg = types.ModuleType("OffSet")
        pkg.__package__ = "OffSet"
        pkg.__spec__ = importlib.machinery.ModuleSpec("OffSet", loader=None, is_package=True)
        sys.modules["OffSet"] = pkg
    pkg.__path__ = [str(ml_root)]
    pkg.__spec__.submodule_search_locations = [str(ml_root)]
