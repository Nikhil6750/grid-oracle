"""
Full automated pre-race pipeline. Run this before every Grand Prix.
It detects what data is available, ingests missing sessions, rebuilds features,
and outputs a final podium prediction.

Usage:
    python scripts/pre_race_pipeline.py --season 2026 --round 5
    python scripts/pre_race_pipeline.py --auto    # finds upcoming round automatically
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
import os; os.chdir(ROOT_DIR)

def run_step(cmd: list, step_name: str):
    print(f"\n{'='*60}")
    print(f"STEP: {step_name}")
    print(f"CMD : {' '.join(cmd)}")
    print('='*60)
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"[WARN] {step_name} exited with code {result.returncode}")
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', type=int, default=2026)
    parser.add_argument('--round', type=int, required=False)
    parser.add_argument('--auto', action='store_true')
    parser.add_argument('--retrain', action='store_true',
                        help='Retrain models after ingesting new session data')
    args = parser.parse_args()

    season = args.season
    # If --auto, detect the upcoming round from fastf1 schedule
    if args.auto or not args.round:
        from scripts.ingest_latest_session import find_current_active_round
        round_num = find_current_active_round(season)
        print(f"Auto-detected upcoming round: {season} R{round_num}")
    else:
        round_num = args.round

    # Detect best available stage
    session_dir = ROOT_DIR / f"data/processed/sessions/season={season}/round={round_num:02d}"
    has_sprint   = (session_dir / "S_results.parquet").exists()
    has_quali    = (session_dir / "Q_results.parquet").exists()
    stage = 'post_sprint' if has_sprint else ('post_qualifying' if has_quali else 'pre_weekend')
    print(f"Prediction stage: {stage}")

    # Step 1: Ingest any new sessions
    run_step(['python', 'scripts/ingest_latest_session.py',
              '--season', str(season), '--round', str(round_num)],
             "Ingest latest session data")

    # Step 2: Generate/update features for the target round
    if stage == 'pre_weekend':
        run_step(['python', 'scripts/generate_upcoming_race_features.py',
                  '--season', str(season), '--round', str(round_num), '--force'],
                 "Generate pre_weekend features")
    else:
        run_step(['python', 'scripts/build_features.py',
                  '--season', str(season), '--stage', stage],
                 f"Build {stage} features")

    # Step 3: Optional retrain
    if args.retrain:
        run_step(['python', 'scripts/train_advanced.py', '--stage', stage],
                 f"Retrain models for {stage}")

    # Step 4: Predict and save
    from src.api.prediction_service import run_prediction
    try:
        result = run_prediction(season=season, round_num=round_num, stage=stage, save_parquet=True)
    except Exception as e:
        print(f"\n[ERROR] Prediction failed: {e}")
        return

    out_path = ROOT_DIR / f"reports/pre_race_prediction_{season}_R{round_num:02d}_{stage}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"PITWALL AI — {season} Round {round_num} ({stage.upper()})")
    print(f"{'='*60}")
    pos_pred = result.get('podium_position_prediction', {})
    if pos_pred:
        print(f"  P1 (WINNER) : {pos_pred.get('P1', 'TBD')}")
        print(f"  P2          : {pos_pred.get('P2', 'TBD')}")
        print(f"  P3          : {pos_pred.get('P3', 'TBD')}")
    else:
        print(f"  Race Winner : {result.get('race_winner_candidate', 'TBD')}")
        for i, e in enumerate(result.get('podium_ranking', [])[:3], 1):
            print(f"  P{i}          : {e['driver']} ({e['probability']*100:.1f}%)")
    print(f"\nFull prediction saved to: {out_path.name}")
    print(f"Warnings: {result.get('warnings', [])}")

if __name__ == '__main__':
    main()
