"""
Shared prediction service used by both scripts/predict_advanced.py and src/api/main.py.
Loads models, runs inference, returns structured results. Does NOT train.
"""
import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from src.modeling.model_registry import ModelRegistry

logger = logging.getLogger(__name__)
_SERVICE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SERVICE_DIR.parent.parent


def _load_model_with_fallback(adv_registry, base_registry, adv_name, base_name):
    """Try advanced model, fallback to baseline. Returns (model, label, is_fallback)."""
    try:
        model = adv_registry.load_model(adv_name)
        return model, "advanced", False
    except FileNotFoundError:
        pass
    try:
        model = base_registry.load_model(base_name)
        return model, "baseline", True
    except FileNotFoundError:
        return None, None, False


def _check_naive_warning(stage: str, task: str) -> str | None:
    """Check if advanced model underperforms naive on the test metric."""
    metrics_path = PROJECT_ROOT / "reports/advanced_metrics.json"
    if not metrics_path.exists():
        return None
    with open(metrics_path, "r") as f:
        data = json.load(f)
    key = f"{task}_{stage}"
    if key not in data or "test" not in data[key]:
        return None
    test_metrics = data[key]["test"]

    if task in ["qualifying", "race_finish"]:
        model_mae = test_metrics.get("mae")
        naive_mae = test_metrics.get("mae_naive")
        if model_mae and naive_mae and model_mae > naive_mae:
            return f"{task} advanced MAE ({model_mae:.3f}) worse than naive ({naive_mae:.3f})"
    else:
        model_val = test_metrics.get("roc_auc")
        naive_val = test_metrics.get("roc_auc_naive")
        if model_val and naive_val and model_val < naive_val:
            return f"{task} advanced ROC AUC ({model_val:.3f}) worse than naive ({naive_val:.3f})"
    return None


def run_prediction(season: int, round_num: int, stage: str, save_parquet: bool = False) -> dict:
    """
    Run inference for a given season/round/stage.
    Returns a dict matching PredictionResponse schema.
    Raises FileNotFoundError if no feature data found.
    """
    adv_registry = ModelRegistry(
        models_dir=str(PROJECT_ROOT / "models/advanced"),
        metrics_filename="advanced_metrics.json",
        predictions_filename="advanced_predictions.parquet",
        reports_dir=str(PROJECT_ROOT / "reports"),
    )
    base_registry = ModelRegistry(
        models_dir=str(PROJECT_ROOT / "models/baseline"),
        metrics_filename="baseline_metrics.json",
        predictions_filename="baseline_predictions.parquet",
        reports_dir=str(PROJECT_ROOT / "reports"),
    )

    # Forbidden columns that must never reach the model at inference time.
    # These columns exist in the parquet for historical/training purposes but are
    # target leakage for an upcoming race. LeakageGuard will reject them even when NaN.
    _FORBIDDEN_AT_INFERENCE = [
        'race_finish_position', 'finishing_position', 'classified_position',
        'classifiedposition', 'position', 'points', 'status', 'podium',
        'top10', 'winner', 'result', 'grid_position', 'race_result',
    ]

    def _strip_forbidden(df: pd.DataFrame) -> pd.DataFrame:
        to_drop = [
            c for c in df.columns
            if c in _FORBIDDEN_AT_INFERENCE
            or c.lower().startswith('target_')
            or '_target' in c.lower()
        ]
        if to_drop:
            logger.info(f"[prediction] Stripping {len(to_drop)} forbidden/target columns at inference: {to_drop}")
            df = df.drop(columns=to_drop)
        return df

    # ---- Load features ----
    q_df = pd.DataFrame()
    if stage == "pre_weekend":
        q_features = pd.read_parquet(str(PROJECT_ROOT / "data/features/qualifying_features.parquet"))
        q_df = q_features[
            (q_features["season"] == season)
            & (q_features["round"] == round_num)
            & (q_features["prediction_stage"] == stage)
        ]
        q_df = _strip_forbidden(q_df)

    r_features = pd.read_parquet(str(PROJECT_ROOT / "data/features/race_features.parquet"))
    r_df = r_features[
        (r_features["season"] == season)
        & (r_features["round"] == round_num)
        & (r_features["prediction_stage"] == stage)
    ]
    r_df = _strip_forbidden(r_df)

    if r_df.empty:
        logger.warning(f"[prediction] r_df is empty for {season} R{round_num} [{stage}]")
        raise FileNotFoundError(
            f"No features for season {season} round {round_num} stage {stage}."
        )

    logger.info(f"[prediction] Loaded {len(r_df)} race feature rows for {season} R{round_num} [{stage}]")

    predictions = []
    models_used: dict[str, str | None] = {}
    warnings: list[str] = []

    if stage == "pre_weekend":
        warnings.append(
            "Pre-weekend prediction: does not use qualifying or session data."
        )

    # ---- Qualifying ----
    pole_sitter = None
    if stage == "pre_weekend" and not q_df.empty:
        model, label, is_fb = _load_model_with_fallback(
            adv_registry, base_registry,
            "qualifying_advanced_pre_weekend", "qualifying_baseline_pre_weekend",
        )
        if model is not None:
            models_used["qualifying"] = label
            if is_fb:
                warnings.append("Qualifying: using baseline fallback model.")
            q_preds = model.predict(q_df)
            for idx, (_, row) in enumerate(q_df.iterrows()):
                predictions.append({
                    "season": row["season"], "round": row["round"],
                    "event_name": row["event_name"], "driver_code": row["driver_code"],
                    "prediction_stage": stage, "task": "qualifying_position",
                    "prediction": float(q_preds[idx]), "probability": None,
                })
            pole_sitter = q_df.iloc[int(np.argmin(q_preds))]["driver_code"]
            logger.info(f"[prediction] Pole sitter candidate: {pole_sitter} (model: {label})")
            w = _check_naive_warning(stage, "qualifying")
            if w:
                warnings.append(w)

    # ---- Race Finish ----
    race_winner = None
    model, label, is_fb = _load_model_with_fallback(
        adv_registry, base_registry,
        f"race_finish_advanced_{stage}", f"race_finish_baseline_{stage}",
    )
    if model is not None:
        models_used["race_finish"] = label
        if is_fb:
            warnings.append("Race Finish: using baseline fallback model.")
        r_preds = model.predict(r_df)
        for idx, (_, row) in enumerate(r_df.iterrows()):
            predictions.append({
                "season": row["season"], "round": row["round"],
                "event_name": row["event_name"], "driver_code": row["driver_code"],
                "prediction_stage": stage, "task": "race_finish_position",
                "prediction": float(r_preds[idx]), "probability": None,
            })
        race_winner = r_df.iloc[int(np.argmin(r_preds))]["driver_code"]
        logger.info(f"[prediction] Race winner candidate: {race_winner} (model: {label})")
        w = _check_naive_warning(stage, "race_finish")
        if w:
            warnings.append(w)

    # ---- Podium ----
    podium_ranking: list[dict] = []
    model, label, is_fb = _load_model_with_fallback(
        adv_registry, base_registry,
        f"podium_advanced_{stage}", f"podium_baseline_{stage}",
    )
    if model is not None:
        models_used["podium"] = label
        if is_fb:
            warnings.append("Podium: using baseline fallback model.")
        p_preds = model.predict(r_df)
        p_proba = (
            model.predict_proba(r_df)[:, 1]
            if hasattr(model, "predict_proba")
            else np.zeros(len(r_df))
        )
        for idx, (_, row) in enumerate(r_df.iterrows()):
            predictions.append({
                "season": row["season"], "round": row["round"],
                "event_name": row["event_name"], "driver_code": row["driver_code"],
                "prediction_stage": stage, "task": "podium_class",
                "prediction": float(p_preds[idx]),
                "probability": float(p_proba[idx]),
            })
        sorted_idx = np.argsort(-p_proba)[:5]
        podium_ranking = [
            {"driver": r_df.iloc[i]["driver_code"], "probability": round(float(p_proba[i]), 4)}
            for i in sorted_idx
        ]
        w = _check_naive_warning(stage, "podium")
        if w:
            warnings.append(w)

    # ---- Podium Position Ranker (P1/P2/P3) ----
    podium_position_prediction: dict = {}
    if podium_ranking:
        top5_codes = [e["driver"] for e in podium_ranking[:5]]
        top5_df = r_df[r_df["driver_code"].isin(top5_codes)].copy()

        ranker, rnk_label, rnk_fb = _load_model_with_fallback(
            adv_registry, base_registry,
            f"podium_ranker_advanced_{stage}", f"podium_ranker_baseline_{stage}",
        )
        if ranker is not None and not top5_df.empty:
            models_used["podium_ranker"] = rnk_label
            if rnk_fb:
                warnings.append("Podium Ranker: using baseline fallback model.")
            pos_preds = ranker.predict(top5_df)
            pos_proba = ranker.predict_proba(top5_df)
            for idx, (_, row) in enumerate(top5_df.iterrows()):
                for class_idx, pos in enumerate(ranker.classes_):
                    predictions.append({
                        "season": row["season"], "round": row["round"],
                        "event_name": row["event_name"], "driver_code": row["driver_code"],
                        "prediction_stage": stage, "task": f"podium_position_P{pos}",
                        "prediction": float(pos_preds[idx]),
                        "probability": float(pos_proba[idx][class_idx]),
                    })
            
            position_map = {}
            for pos in [1, 2, 3]:
                if pos not in ranker.classes_:
                    continue
                class_idx = list(ranker.classes_).index(pos)
                probs_for_pos = {
                    top5_df.iloc[i]["driver_code"]: pos_proba[i][class_idx]
                    for i in range(len(top5_df))
                }
                if probs_for_pos:
                    position_map[f"P{pos}"] = max(probs_for_pos, key=probs_for_pos.get)
            podium_position_prediction = position_map

    # ---- Top 10 ----
    top10_ranking: list[dict] = []
    model, label, is_fb = _load_model_with_fallback(
        adv_registry, base_registry,
        f"top10_advanced_{stage}", f"top10_baseline_{stage}",
    )
    if model is not None:
        models_used["top10"] = label
        if is_fb:
            warnings.append("Top 10: using baseline fallback model.")
        t_preds = model.predict(r_df)
        t_proba = (
            model.predict_proba(r_df)[:, 1]
            if hasattr(model, "predict_proba")
            else np.zeros(len(r_df))
        )
        for idx, (_, row) in enumerate(r_df.iterrows()):
            predictions.append({
                "season": row["season"], "round": row["round"],
                "event_name": row["event_name"], "driver_code": row["driver_code"],
                "prediction_stage": stage, "task": "top10",
                "prediction": float(t_preds[idx]),
                "probability": float(t_proba[idx]),
            })
        sorted_idx = np.argsort(-t_proba)[:10]
        top10_ranking = [
            {"driver": r_df.iloc[i]["driver_code"], "probability": round(float(t_proba[i]), 4)}
            for i in sorted_idx
        ]
        w = _check_naive_warning(stage, "top10")
        if w:
            warnings.append(w)

    # ---- Guard ----
    if not predictions:
        raise RuntimeError(
            "No predictions generated. Check models in models/advanced/ or models/baseline/."
        )

    # ---- Save ----
    if save_parquet:
        preds_df = pd.DataFrame(predictions)
        adv_registry.append_predictions(preds_df)

    return {
        "season": season,
        "round": round_num,
        "stage": stage,
        "pole_sitter_candidate": pole_sitter,
        "race_winner_candidate": race_winner,
        "podium_ranking": podium_ranking,
        "podium_position_prediction": podium_position_prediction,
        "top10_ranking": top10_ranking,
        "models_used": models_used,
        "warnings": warnings,
        "prediction_records_path": "reports/advanced_predictions.parquet",
    }
