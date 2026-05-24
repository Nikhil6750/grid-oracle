import sys
from pathlib import Path
import argparse
import pandas as pd

# Add src to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.modeling.model_registry import ModelRegistry

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--stage", type=str, choices=["pre_weekend", "post_qualifying"], required=True)
    args = parser.parse_args()
    
    registry = ModelRegistry()
    
    # Load features based on stage
    if args.stage == 'pre_weekend':
        q_features = pd.read_parquet("data/features/qualifying_features.parquet")
        r_features = pd.read_parquet("data/features/race_features.parquet")
    else:
        # For post_qualifying we only predict race
        r_features = pd.read_parquet("data/features/race_features.parquet")
        
    # Filter for the specific event
    if args.stage == 'pre_weekend':
        q_df = q_features[(q_features['season'] == args.season) & (q_features['round'] == args.round) & (q_features['prediction_stage'] == args.stage)]
    r_df = r_features[(r_features['season'] == args.season) & (r_features['round'] == args.round) & (r_features['prediction_stage'] == args.stage)]
    
    if r_df.empty:
        print(f"No features found for season {args.season} round {args.round} at stage {args.stage}.")
        return

    predictions = []
    
    # Run predictions
    if args.stage == 'pre_weekend':
        try:
            q_model = registry.load_model('qualifying_baseline_pre_weekend')
            q_preds = q_model.predict(q_df)
            for idx, (_, row) in enumerate(q_df.iterrows()):
                predictions.append({
                    'season': row['season'],
                    'round': row['round'],
                    'event_name': row['event_name'],
                    'driver_code': row['driver_code'],
                    'prediction_stage': args.stage,
                    'task': 'qualifying_position',
                    'prediction': float(q_preds[idx]),
                    'probability': None
                })
        except FileNotFoundError:
            print("Warning: qualifying_baseline_pre_weekend model not found.")

    try:
        r_model = registry.load_model(f'race_finish_baseline_{args.stage}')
        r_preds = r_model.predict(r_df)
        for idx, (_, row) in enumerate(r_df.iterrows()):
            predictions.append({
                'season': row['season'],
                'round': row['round'],
                'event_name': row['event_name'],
                'driver_code': row['driver_code'],
                'prediction_stage': args.stage,
                'task': 'race_finish_position',
                'prediction': float(r_preds[idx]),
                'probability': None
            })
    except FileNotFoundError:
        print(f"Warning: race_finish_baseline_{args.stage} model not found.")

    try:
        p_model = registry.load_model(f'podium_baseline_{args.stage}')
        p_preds = p_model.predict(r_df)
        p_proba = p_model.predict_proba(r_df)[:, 1] if hasattr(p_model, 'predict_proba') else [None]*len(r_df)
        for idx, (_, row) in enumerate(r_df.iterrows()):
            predictions.append({
                'season': row['season'],
                'round': row['round'],
                'event_name': row['event_name'],
                'driver_code': row['driver_code'],
                'prediction_stage': args.stage,
                'task': 'podium_class',
                'prediction': float(p_preds[idx]),
                'probability': float(p_proba[idx]) if p_proba[idx] is not None else None
            })
    except FileNotFoundError:
        print(f"Warning: podium_baseline_{args.stage} model not found.")

    try:
        t_model = registry.load_model(f'top10_baseline_{args.stage}')
        t_preds = t_model.predict(r_df)
        t_proba = t_model.predict_proba(r_df)[:, 1] if hasattr(t_model, 'predict_proba') else [None]*len(r_df)
        for idx, (_, row) in enumerate(r_df.iterrows()):
            predictions.append({
                'season': row['season'],
                'round': row['round'],
                'event_name': row['event_name'],
                'driver_code': row['driver_code'],
                'prediction_stage': args.stage,
                'task': 'top10',
                'prediction': float(t_preds[idx]),
                'probability': float(t_proba[idx]) if t_proba[idx] is not None else None
            })
    except FileNotFoundError:
        print(f"Warning: top10_baseline_{args.stage} model not found.")

    if not predictions:
        print("No predictions generated.")
        return

    preds_df = pd.DataFrame(predictions)
    
    print("\n" + "="*50)
    print(f"PREDICTION SUMMARY: {args.season} Round {args.round} ({args.stage})")
    print("="*50)
    
    # 1. Pole Sitter
    task_df = preds_df[preds_df['task'] == 'qualifying_position']
    pole_sitter = None
    if not task_df.empty:
        best_idx = task_df['prediction'].idxmin()
        best = task_df.loc[best_idx]
        pole_sitter = f"{best['driver_code']} ({best['prediction']:.2f})"
        print(f"Predicted Pole Sitter:           {pole_sitter}")
        
    # 2. Race Winner Candidate
    task_df = preds_df[preds_df['task'] == 'race_finish_position']
    race_winner = None
    if not task_df.empty:
        best_idx = task_df['prediction'].idxmin()
        best = task_df.loc[best_idx]
        race_winner = f"{best['driver_code']} ({best['prediction']:.2f})"
        print(f"Lowest predicted race finish:    {race_winner}")
        print(f"Predicted Race Winner Candidate: {race_winner}")

    # 3. Podium Candidates
    task_df = preds_df[preds_df['task'] == 'podium_class']
    if not task_df.empty:
        positive_preds = task_df.sort_values(by='probability', ascending=False).head(5)
        podium_candidates = ", ".join([f"{r['driver_code']} ({r['probability']:.2f})" for _, r in positive_preds.iterrows()])
        print(f"Podium Probability Ranking:      {podium_candidates}")

    # 4. Top 10 Candidates
    task_df = preds_df[preds_df['task'] == 'top10']
    if not task_df.empty:
        positive_preds = task_df.sort_values(by='probability', ascending=False).head(10)
        top10_candidates = ", ".join([f"{r['driver_code']} ({r['probability']:.2f})" for _, r in positive_preds.iterrows()])
        print(f"Top 10 Probability Ranking:      {top10_candidates}")
        
    print("\n" + "-"*50)
    print("WARNING: Baseline model only. Advanced ranking and simulation models will improve this in later phases.")
    print("-"*50 + "\n")
    
    # Save to parquet
    registry.append_predictions(preds_df)
    print(f"Saved {len(preds_df)} prediction records to reports/baseline_predictions.parquet")

if __name__ == "__main__":
    main()
