"""Loads the trained models saved by scripts/train.py and serves predictions."""

import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from app.config import get_settings
from app.ml.features import FEATURE_COLUMNS, to_row

BACKEND_DIR = Path(__file__).resolve().parents[2]


def model_dir() -> Path:
    p = Path(get_settings().model_dir)
    return p if p.is_absolute() else BACKEND_DIR / p


class ModelUnavailable(Exception):
    pass


@lru_cache
def _bundle(mtime: float) -> dict:  # mtime in the key reloads the file after retraining
    return joblib.load(model_dir() / "model.joblib")


def load_bundle() -> dict:
    path = model_dir() / "model.joblib"
    if not path.exists():
        raise ModelUnavailable("No trained model found. Run: python -m scripts.train")
    return _bundle(path.stat().st_mtime)


def load_metrics() -> dict:
    path = model_dir() / "metrics.json"
    if not path.exists():
        raise ModelUnavailable("No metrics found. Run: python -m scripts.train")
    return json.loads(path.read_text(encoding="utf-8"))


def predict(features: dict, model: str = "selected") -> tuple[str, float, float]:
    bundle = load_bundle()
    name = bundle["selected_model"] if model == "selected" else model
    if name not in bundle["models"]:
        raise ModelUnavailable(f"Model '{name}' is not available")
    entry = bundle["models"][name]
    frame = pd.DataFrame([to_row(features)], columns=FEATURE_COLUMNS).astype(float)
    probability = float(entry["pipeline"].predict_proba(frame)[0, 1])
    return name, probability, float(entry["threshold"])
