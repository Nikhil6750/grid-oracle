"""
Live race prediction service.

Loads the bucketed live models trained by ``scripts/train_live_model.py`` and
turns a stream of lap data into per-driver final-position predictions, picking
the correct model for the current race progress.
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.feature_engineering.mid_race_features import MidRaceFeatureBuilder

MODELS_DIR = Path("models/live")

# (bucket name, upper-inclusive pct_complete threshold, filename)
_BUCKET_FILES = [
    ("early", 0.25, "live_race_early.joblib"),
    ("mid", 0.60, "live_race_mid.joblib"),
    ("late", 1.01, "live_race_late.joblib"),
]


class LiveRacePredictor:
    """Predicts final finishing positions from in-race lap data."""

    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = Path(models_dir)
        self._models: dict[str, dict] = {}
        self._load_models()

    def _load_models(self) -> None:
        for name, _thresh, filename in _BUCKET_FILES:
            path = self.models_dir / filename
            if path.exists():
                try:
                    self._models[name] = joblib.load(path)
                except Exception as e:  # pragma: no cover - defensive
                    print(f"[LiveRacePredictor] Failed to load {path}: {e}")

    @property
    def is_ready(self) -> bool:
        return len(self._models) > 0

    @staticmethod
    def _bucket_for_pct(pct_complete: float) -> str:
        for name, thresh, _ in _BUCKET_FILES:
            if pct_complete <= thresh:
                return name
        return "late"

    def _select_model(self, pct_complete: float) -> dict | None:
        """Return the bucket model for the given progress, with fallback."""
        preferred = self._bucket_for_pct(pct_complete)
        if preferred in self._models:
            return self._models[preferred]
        # Fall back to any available model so we still return a prediction.
        for name, _, _ in _BUCKET_FILES:
            if name in self._models:
                return self._models[name]
        return None

    def predict_from_laps(
        self,
        laps_df: pd.DataFrame,
        lap_n: int,
        total_laps: int,
        event_name: str | None = None,
        is_street_circuit: bool | None = None,
    ) -> dict:
        """Predict final positions from lap data available at ``lap_n``.

        Returns a dict keyed by driver code::

            {
                "VER": {"predicted_position": 1, "win_probability": 0.62,
                         "podium_probability": 0.91, "current_position": 1,
                         "tyre_compound": 2.0, "tyre_life": 12.0,
                         "pit_stops_done": 1.0},
                ...
            }

        sorted so that the lowest predicted position comes first.
        """
        pct_complete = (lap_n / total_laps) if total_laps else 0.0

        builder = MidRaceFeatureBuilder(
            laps_df,
            total_laps=total_laps,
            is_street_circuit=is_street_circuit,
            event_name=event_name,
        )
        feats = builder.build_features_at_lap(lap_n)
        if feats.empty:
            return {}

        model_payload = self._select_model(pct_complete)
        driver_codes = feats["driver_code"].tolist()
        current_positions = feats["current_position"].tolist()

        if model_payload is None:
            # No model available: fall back to current position as prediction.
            raw_pred = np.array(current_positions, dtype=float)
        else:
            model = model_payload["model"]
            feature_cols = model_payload["feature_cols"]
            X = feats.reindex(columns=feature_cols, fill_value=0.0)
            raw_pred = np.asarray(model.predict(X), dtype=float)

        results = self._assemble(feats, driver_codes, current_positions, raw_pred)
        return results

    @staticmethod
    def _assemble(feats, driver_codes, current_positions, raw_pred) -> dict:
        """Rank predictions and derive win/podium probabilities."""
        order = np.argsort(raw_pred, kind="stable")
        ranked_positions = {}
        for rank, idx in enumerate(order, start=1):
            ranked_positions[idx] = rank

        # Convert raw predicted positions to probabilities via a softmax over the
        # negative predicted position: lower predicted position -> higher prob.
        scores = -raw_pred
        scores = scores - scores.max()
        exp = np.exp(scores)
        win_probs = exp / exp.sum() if exp.sum() > 0 else np.zeros_like(exp)

        # Podium probability: probability mass of finishing in the top 3.
        # Approximate using the same softmax but over a temperature that spreads
        # the top of the field, then renormalise the top contenders.
        podium_scores = -raw_pred / 2.0
        podium_scores = podium_scores - podium_scores.max()
        podium_exp = np.exp(podium_scores)
        podium_norm = podium_exp / podium_exp.sum() if podium_exp.sum() > 0 else podium_exp
        # Scale so the expected number of podium finishers is ~3.
        podium_probs = np.clip(podium_norm * 3.0, 0.0, 1.0)

        out = {}
        for idx, code in enumerate(driver_codes):
            out[code] = {
                "predicted_position": int(ranked_positions[idx]),
                "predicted_position_raw": round(float(raw_pred[idx]), 3),
                "win_probability": round(float(win_probs[idx]), 4),
                "podium_probability": round(float(podium_probs[idx]), 4),
                "current_position": (
                    int(current_positions[idx])
                    if current_positions[idx] == current_positions[idx]
                    else None
                ),
                "tyre_compound": float(feats.iloc[idx]["tyre_compound"]),
                "tyre_life": float(feats.iloc[idx]["tyre_life"]),
                "pit_stops_done": float(feats.iloc[idx]["pit_stops_done"]),
            }

        # Sort by predicted_position ascending.
        return dict(
            sorted(out.items(), key=lambda kv: kv[1]["predicted_position"])
        )
