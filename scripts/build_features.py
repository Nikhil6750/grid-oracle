import sys
import argparse
from pathlib import Path
import pandas as pd

# Add src to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.feature_engineering.feature_store import FeatureStore

def main():
    parser = argparse.ArgumentParser(description="Build PitWall AI feature store")
    parser.add_argument("--start-year", type=int, help="Start year for feature building")
    parser.add_argument("--end-year", type=int, help="End year for feature building")
    parser.add_argument("--season", type=int, help="Specific season to build features for")
    parser.add_argument("--stage", type=str, choices=["pre_weekend", "post_qualifying", "post_sprint"], help="Prediction stage filter")
    parser.add_argument("--validate-only", action="store_true", help="Run the pipeline but exit(1) if validation fails, print metrics")
    
    args = parser.parse_args()
    
    store = FeatureStore()
    
    print(f"Building Feature Store...")
    if args.season:
        print(f"Filtering to season: {args.season}")
    if args.start_year and args.end_year:
        print(f"Filtering to year range: {args.start_year}-{args.end_year}")
    if args.stage:
        print(f"Filtering to stage: {args.stage}")
        
    metadata = store.build(
        season_filter=args.season,
        stage_filter=args.stage,
        start_year=args.start_year,
        end_year=args.end_year,
    )
    
    # Output Summary
    print("\n" + "="*60)
    print("FEATURE STORE BUILD SUMMARY")
    print("="*60)
    
    rows = metadata.get('rows', {})
    total_rows = sum(rows.values()) - rows.get('targets', 0) # don't double count targets
    print(f"Total Feature Rows: {total_rows}")
    print("\nRows by table:")
    for k, v in rows.items():
        print(f"  {k}: {v}")
        
    print("\nOutput Files:")
    out_dir = Path("data/features")
    for p in out_dir.glob("*.parquet"):
        print(f"  {p}")
    for p in out_dir.glob("*.json"):
        print(f"  {p}")
        
    # Check distributions and missing values
    try:
        if (out_dir / "targets.parquet").exists():
            tdf = pd.read_parquet(out_dir / "targets.parquet")
            print("\nTarget Distribution (Podium Class):")
            print(tdf['target_podium_class'].value_counts().to_string())
            
        print("\nMissing Values Summary:")
        for table in ["qualifying_features", "race_features", "sprint_features"]:
            p = out_dir / f"{table}.parquet"
            if p.exists():
                df = pd.read_parquet(p)
                missing = df.isna().sum()
                missing = missing[missing > 0]
                if not missing.empty:
                    print(f"  {table}:")
                    print(missing.to_string())
                else:
                    print(f"  {table}: 0 missing values")

        # Rows by season for each table
        for table in ["qualifying_features", "race_features"]:
            p = out_dir / f"{table}.parquet"
            if p.exists():
                df = pd.read_parquet(p)
                print(f"\n{table.replace('_', ' ').title()} by Season:")
                print(df['season'].value_counts().sort_index().to_string())
                print(f"\n{table.replace('_', ' ').title()} by Stage:")
                print(df['prediction_stage'].value_counts().to_string())
                    
    except Exception as e:
        print(f"Error printing metrics: {e}")
        
    # Skipped events report
    skipped = metadata.get('skipped_events', [])
    if skipped:
        print("\n" + "="*60)
        print(f"SKIPPED EVENTS ({len(skipped)})")
        print("="*60)
        for ev in skipped:
            print(f"  Season {ev['season']} Round {ev['round']} ({ev.get('session_type','?')}): {ev['reason']}")
        
    # Leakage report
    print("\n" + "="*60)
    print("LEAKAGE VALIDATION REPORT")
    print("="*60)
    is_valid = metadata.get('is_valid', False)
    errors = metadata.get('errors', [])
    
    if is_valid:
        print("[PASS] No data leakage detected.")
    else:
        print(f"[FAIL] {len(errors)} leakage issues detected:")
        for err in errors:
            print(f"  - {err}")
            
    if args.validate_only and not is_valid:
        print("\nExiting with code 1 due to validation errors (--validate-only flag passed)")
        sys.exit(1)
        
    if not is_valid:
        sys.exit(1) # We should always fail the build script if there is leakage
        
if __name__ == "__main__":
    main()
