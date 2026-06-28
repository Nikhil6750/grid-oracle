"""
PitWall AI — CLI Advanced Predictions
Uses shared prediction_service for inference logic.
"""
import sys
from pathlib import Path
import argparse
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.api.prediction_service import run_prediction


def main():
    parser = argparse.ArgumentParser(description="PitWall AI Advanced Predictions")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--stage", type=str, choices=["pre_weekend", "post_qualifying"], required=True)
    args = parser.parse_args()

    try:
        result = run_prediction(season=args.season, round_num=args.round, stage=args.stage, save_parquet=True)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    except RuntimeError as e:
        print(f"Error: {e}")
        return

    # --- Console Output ---
    print(f"\n{'='*60}")
    print(f"  PREDICTION SUMMARY: {args.season} Round {args.round} ({args.stage})")
    print(f"{'='*60}")

    if result["pole_sitter_candidate"]:
        print(f"  Predicted Pole Sitter:           {result['pole_sitter_candidate']}")

    if result["race_winner_candidate"]:
        print(f"  Predicted Race Winner Candidate:  {result['race_winner_candidate']}")

    if result["podium_ranking"]:
        podium_str = ", ".join([f"{d['driver']} ({d['probability']:.2f})" for d in result["podium_ranking"]])
        print(f"  Podium Probability Ranking:       {podium_str}")

    if result["top10_ranking"]:
        top10_str = ", ".join([f"{d['driver']} ({d['probability']:.2f})" for d in result["top10_ranking"]])
        print(f"  Top 10 Probability Ranking:       {top10_str}")

    print(f"\n  Models Used:")
    for task, label in result["models_used"].items():
        print(f"    - {task.replace('_', ' ').title()}: {label}")

    if result["warnings"]:
        print(f"\n  Warnings:")
        for w in result["warnings"]:
            print(f"    ! {w}")

    print(f"\n{'='*60}\n")
    print(f"Saved prediction records to {result['prediction_records_path']}")

    # --- Unified Prediction ---
    preds_df = pd.read_parquet(ROOT_DIR / result["prediction_records_path"])
    preds_df = preds_df[
        (preds_df["season"] == args.season)
        & (preds_df["round"] == args.round)
        & (preds_df["prediction_stage"] == args.stage)
    ].drop_duplicates(subset=["driver_code", "task"], keep="last")

    finish_df = preds_df[preds_df["task"] == "race_finish_position"][
        ["driver_code", "prediction"]
    ].rename(columns={"prediction": "race_finish_pred"})
    podium_df = preds_df[preds_df["task"] == "podium_class"][
        ["driver_code", "probability"]
    ].rename(columns={"probability": "podium_proba"})

    race_features = pd.read_parquet(ROOT_DIR / "data/features/race_features.parquet")
    quali_df = race_features[
        (race_features["season"] == args.season)
        & (race_features["round"] == args.round)
        & (race_features["prediction_stage"] == args.stage)
    ][["driver_code", "quali_gap_to_pole_s"]]

    unified_df = finish_df.merge(podium_df, on="driver_code", how="inner").merge(
        quali_df, on="driver_code", how="left"
    )

    print(f"\n{'='*60}")
    print(f"  UNIFIED PREDICTION (Top 5)")
    print(f"  35% Race Finish + 40% Podium Probability + 25% Qualifying")
    print(f"{'='*60}")

    if unified_df.empty:
        print("  Insufficient data: race_finish_position and/or podium_class")
        print("  predictions not available for this season/round/stage.")
    else:
        n = len(unified_df)
        denom = max(n - 1, 1)

        finish_score = (1 - (unified_df["race_finish_pred"] - 1) / denom).clip(0, 1)

        has_quali = unified_df["quali_gap_to_pole_s"].notna().any()
        grid_rank = unified_df["quali_gap_to_pole_s"].rank(method="min", na_option="bottom")
        quali_score = (1 - (grid_rank - 1) / denom).clip(0, 1)

        unified_df["grid"] = grid_rank.astype(int)
        unified_df["unified_score"] = (
            0.35 * finish_score + 0.40 * unified_df["podium_proba"] + 0.25 * quali_score
        )

        unified_df = unified_df.sort_values("unified_score", ascending=False).reset_index(drop=True)

        bar_width = 20
        for _, row in unified_df.head(5).iterrows():
            grid_str = f"P{row['grid']}" if has_quali else "N/A"
            bar_len = int(round(row["unified_score"] * bar_width))
            bar = "#" * bar_len + "-" * (bar_width - bar_len)
            print(
                f"  {row['driver_code']:<4} Grid: {grid_str:<4} "
                f"Score: {row['unified_score']:.3f}  Podium: {row['podium_proba']:.1%}  {bar}"
            )

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
