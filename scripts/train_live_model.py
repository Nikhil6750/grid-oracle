"""
Train the live race prediction models.

Loads ``data/features/mid_race_features.parquet`` and trains three XGBoost
regressors that predict each driver's *final* finishing position from the
mid-race situation, bucketed by how far the race has progressed:

    early_model : snapshots with pct_complete in (0.00, 0.25]
    mid_model   : snapshots with pct_complete in (0.25, 0.60]
    late_model  : snapshots with pct_complete in (0.60, 1.00]

Models are saved to ``models/live/live_race_{early,mid,late}.joblib``.

Recent seasons are weighted more heavily (same scheme as
``scripts/train_advanced.py``) and the split is time-based: older seasons train,
the most recent seasons validate/test. Each model's MAE is printed alongside the
naive baseline (current position == final position).

Run:
    python scripts/train_live_model.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from xgboost import XGBRegressor

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

FEATURES_PATH = ROOT_DIR / "data" / "features" / "mid_race_features.parquet"
MODELS_DIR = ROOT_DIR / "models" / "live"

TARGET_COL = "target_final_position"
ID_COLS = ["season", "round", "lap_n", "pct_complete", "driver_code"]

# Completion buckets: (name, lower_exclusive, upper_inclusive, filename).
BUCKETS = [
    ("early", 0.00, 0.25, "live_race_early.joblib"),
    ("mid", 0.25, 0.60, "live_race_mid.joblib"),
    ("late", 0.60, 1.01, "live_race_late.joblib"),
]


def compute_sample_weights(df: pd.DataFrame) -> np.ndarray:
    """Weight recent seasons more heavily (matches scripts/train_advanced.py)."""
    season_weights = {
        2018: 0.3,
        2019: 0.3,
        2020: 0.4,
        2021: 0.6,
        2022: 1.0,
        2023: 2.0,
        2024: 3.5,
        2025: 5.0,
        2026: 8.0,
    }
    return df["season"].map(season_weights).fillna(1.0).values


def time_based_split(df: pd.DataFrame):
    """Train on older seasons, validate on the second-most-recent, test on newest.

    Falls back gracefully when only a few seasons are present.
    """
    seasons = sorted(df["season"].unique())
    if len(seasons) >= 3:
        test_seasons = seasons[-1:]
        val_seasons = seasons[-2:-1]
        train_seasons = seasons[:-2]
    elif len(seasons) == 2:
        train_seasons, val_seasons, test_seasons = seasons[:1], seasons[1:], seasons[1:]
    else:
        train_seasons = val_seasons = test_seasons = seasons

    train = df[df["season"].isin(train_seasons)]
    val = df[df["season"].isin(val_seasons)]
    test = df[df["season"].isin(test_seasons)]
    return train, val, test, train_seasons, val_seasons, test_seasons


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """All numeric columns except identifiers and the target."""
    return [c for c in df.columns if c not in ID_COLS + [TARGET_COL]]


def train_bucket(name: str, low: float, high: float, filename: str, df: pd.DataFrame):
    bucket = df[(df["pct_complete"] > low) & (df["pct_complete"] <= high)].copy()
    print(f"\n{'=' * 60}")
    print(f"BUCKET: {name}_model  (pct_complete {low:.2f}-{high:.2f})")
    print(f"{'=' * 60}")

    if bucket.empty:
        print("  No rows in this bucket — skipping.")
        return

    feature_cols = get_feature_columns(bucket)
    train, val, test, tr_s, va_s, te_s = time_based_split(bucket)
    print(f"  Rows: {len(bucket)} | Train: {len(train)} Val: {len(val)} Test: {len(test)}")
    print(f"  Train seasons {tr_s} | Val {va_s} | Test {te_s}")

    if train.empty:
        print("  Empty training split — skipping.")
        return

    X_train = train[feature_cols]
    y_train = train[TARGET_COL]
    weights = compute_sample_weights(train)

    model = XGBRegressor(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        objective="reg:squarederror",
    )
    model.fit(X_train, y_train, sample_weight=weights)

    # Evaluate on whichever splits have data; fall back to train if needed.
    for split_name, split_df in [("val", val), ("test", test)]:
        if split_df.empty:
            continue
        y_true = split_df[TARGET_COL]
        y_pred = model.predict(split_df[feature_cols])
        model_mae = mean_absolute_error(y_true, y_pred)
        # Naive baseline: assume the current position is the final position.
        naive_mae = mean_absolute_error(y_true, split_df["current_position"])
        delta = naive_mae - model_mae
        verdict = "better" if delta > 0 else "worse"
        print(
            f"  [{split_name}] Model MAE: {model_mae:.4f} | "
            f"Naive MAE: {naive_mae:.4f} | "
            f"Model is {abs(delta):.4f} {verdict} than naive"
        )

    payload = {
        "model": model,
        "feature_cols": feature_cols,
        "bucket": name,
        "pct_range": [low, high],
        "train_seasons": list(tr_s),
    }
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = MODELS_DIR / filename
    joblib.dump(payload, out_path)
    print(f"  Saved -> {out_path}")


def main() -> None:
    if not FEATURES_PATH.exists():
        raise SystemExit(
            f"Features not found: {FEATURES_PATH}\n"
            "Run scripts/build_mid_race_features.py first."
        )

    df = pd.read_parquet(FEATURES_PATH)
    df = df[df[TARGET_COL].notna()].copy()
    print(f"Loaded {len(df)} rows across seasons {sorted(df['season'].unique())}")

    for name, low, high, filename in BUCKETS:
        train_bucket(name, low, high, filename, df)

    print("\nDone.")


if __name__ == "__main__":
    main()
