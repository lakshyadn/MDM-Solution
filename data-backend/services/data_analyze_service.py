from __future__ import annotations

from importlib import util
from pathlib import Path
from typing import Any, Dict
import os


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = Path(__file__).resolve().parent
FILE_TR_PATH = SERVICES_DIR / "data_analyze_file_tr.py"
ARTIFACTS_DIR = Path(
    os.getenv("DATA_ANALYZE_ARTIFACTS_DIR", str(BACKEND_ROOT / "data_analyze_artifacts"))
)
_CACHED_MODULE = None
_CACHED_MTIME = None


def _load_file_tr_module():
    global _CACHED_MODULE, _CACHED_MTIME

    if not FILE_TR_PATH.exists():
        raise FileNotFoundError(f"Data Analyze module not found at: {FILE_TR_PATH}")

    current_mtime = FILE_TR_PATH.stat().st_mtime
    if _CACHED_MODULE is not None and _CACHED_MTIME == current_mtime:
        return _CACHED_MODULE

    spec = util.spec_from_file_location("data_analyze_file_tr", str(FILE_TR_PATH))
    if spec is None or spec.loader is None:
        raise ImportError("Failed to create import spec for Data Analyze module")

    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    module.MEMORY_FILE = str(ARTIFACTS_DIR / "anomaly_memory.csv")
    module.MODEL_PATH = str(ARTIFACTS_DIR / "anomaly_model.pkl")

    _CACHED_MODULE = module
    _CACHED_MTIME = current_mtime

    return _CACHED_MODULE


def run_data_analyze(file_path: str, sheet: Any = None, duplicate_key: str | None = None) -> Dict[str, Any]:
    module = _load_file_tr_module()

    result = module.analyze_file_for_ui(
        file_path=file_path,
        sheet=sheet,
        duplicate_key=duplicate_key,
    )

    return module.make_json_safe(result)
