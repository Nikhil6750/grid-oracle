"""
PitWall AI — CLI Advanced Predictions
Uses shared prediction_service for inference logic.
"""
import sys
from pathlib import Path
import argparse

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
        result = run_prediction(season=args.season, round_num=args.round, stage=args.stage)
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


if __name__ == "__main__":
    main()
