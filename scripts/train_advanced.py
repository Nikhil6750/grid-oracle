import sys
from pathlib import Path
import argparse
import pandas as pd
import numpy as np

# Add src to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.modeling.data import load_and_join_data, time_based_split, drop_missing_targets
from src.modeling.preprocessing import get_baseline_pipeline
from src.modeling.advanced_models import (
    get_qualifying_advanced_model, get_race_finish_advanced_model, 
    get_podium_advanced_model, get_top10_advanced_model
)
from src.modeling.baseline_models import (
    naive_qualifying_prediction, naive_race_finish_pre_weekend, naive_race_finish_post_qualifying,
    naive_podium_pre_weekend, naive_podium_post_qualifying, naive_top10_pre_weekend, naive_top10_post_qualifying
)
from src.modeling.evaluation import evaluate_regression, evaluate_classification
from src.modeling.model_registry import ModelRegistry
import json
from sklearn.metrics import mean_absolute_error

def _print_pred_debug(task, stage, split_name, pipeline, y_true, y_pred, df):
    """Prints detailed prediction diagnostics for regression tasks."""
    model_step = pipeline.named_steps['model']
    model_class = type(model_step).__name__
    
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)
    
    print(f"\n{'='*60}")
    print(f"[DEBUG-PREDS] {task} | {stage} | {split_name}")
    print(f"{'='*60}")
    print(f"  Model Class:        {model_class}")
    print(f"  Samples:            {len(y_pred_arr)}")
    print(f"  y_true (first 10):  {y_true_arr[:10].tolist()}")
    print(f"  y_pred (first 10):  {np.round(y_pred_arr[:10], 4).tolist()}")
    print(f"  Pred Mean/Std:      {y_pred_arr.mean():.4f} / {y_pred_arr.std():.4f}")
    print(f"  Pred Min/Max:       {y_pred_arr.min():.4f} / {y_pred_arr.max():.4f}")
    print(f"  True Mean/Std:      {y_true_arr.mean():.4f} / {y_true_arr.std():.4f}")
    
    # Direct MAE check
    direct_mae = mean_absolute_error(y_true_arr, y_pred_arr)
    print(f"  Direct MAE:         {direct_mae:.6f}")
    
    # Compare to baseline if available
    from pathlib import Path
    base_metrics_path = Path("reports/baseline_metrics.json")
    if base_metrics_path.exists():
        with open(base_metrics_path, "r") as f:
            base_data = json.load(f)
        key = f"{task}_{stage}"
        if key in base_data and split_name in base_data[key]:
            base_mae = base_data[key][split_name].get('mae')
            if base_mae is not None:
                print(f"  Baseline MAE:       {base_mae:.6f}")
                if abs(direct_mae - base_mae) < 1e-10:
                    print(f"  *** WARNING: Advanced MAE is IDENTICAL to Baseline MAE ***")
                else:
                    diff = direct_mae - base_mae
                    print(f"  MAE Difference:     {diff:+.6f} ({'worse' if diff > 0 else 'better'})")
    
    # Check if predictions are all constant
    if y_pred_arr.std() < 1e-10:
        print(f"  *** WARNING: All predictions are constant ({y_pred_arr[0]:.4f}) ***")
    
    print(f"{'='*60}\n")

def log_input_columns(pipeline, train_df, task, stage, debug=False):
    """Logs the exact columns used by the model to reports/model_input_columns.json."""
    preprocessor = pipeline.named_steps['preprocessor']
    feature_selector = pipeline.named_steps['feature_selector']
    stage_dropper = pipeline.named_steps['stage_dropper']
    
    # Calculate what is dropped and used
    fs_dropped = [c for c in feature_selector.cols_to_drop if c in train_df.columns]
    sd_dropped = getattr(stage_dropper, 'dropped_cols_', [])
    all_dropped = set(fs_dropped + sd_dropped + preprocessor.drop_features)
    
    used_cols = [c for c in train_df.columns if c not in all_dropped]
    
    out_file = Path("reports/advanced_model_input_columns.json")
    if out_file.exists():
        with open(out_file, "r") as f:
            data = json.load(f)
    else:
        data = {}
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
    key = f"{task}_{stage}"
    data[key] = used_cols
    
    with open(out_file, "w") as f:
        json.dump(data, f, indent=4)
        
    if debug:
        print(f"\n[DEBUG] --- {key} ---")
        print(f"[DEBUG] Columns Before Filtering: {len(train_df.columns)}")
        print(f"[DEBUG] Dropped by Target/ID Rules: {len(fs_dropped)}")
        print(f"[DEBUG] Dropped by Stage Rules: {len(sd_dropped)}")
        print(", ".join(sd_dropped) if sd_dropped else "None")
        print(f"[DEBUG] Final Features Used for Modeling: {len(used_cols)}")
        print(", ".join(used_cols))
        
        # Check suspicious
        from src.modeling.preprocessing import LeakageGuard
        lg = LeakageGuard(stage)
        try:
            # We bypass the check during pipeline if we don't fit, but if we do fit, it checks automatically.
            pass
        except Exception as e:
            print(f"[DEBUG] Suspicious leakage detected during fit: {e}")

def train_qualifying(stage, registry):
    print(f"Training Advanced Qualifying Model ({stage})...")
    features = pd.read_parquet("data/features/qualifying_features.parquet")
    features = features[features['prediction_stage'] == stage]
    
    joined = load_and_join_data(features)
    joined = drop_missing_targets(joined, 'target_qualifying_position')
    
    train, val, test = time_based_split(joined)
    print(f"Data Splits -> Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    
    if train.empty:
        raise ValueError("No training data available after dropping missing targets.")
        
    y_train = train['target_qualifying_position']
    y_val = val['target_qualifying_position']
    y_test = test['target_qualifying_position']
    
    pipeline = get_baseline_pipeline(get_qualifying_advanced_model(), stage=stage)
    pipeline.fit(train, y_train)
    
    log_input_columns(pipeline, train, 'qualifying', stage, registry.debug_columns)
    
    for split_name, df, y_true in [('val', val, y_val), ('test', test, y_test)]:
        if df.empty:
            continue
        # Baseline
        preds = pipeline.predict(df)
        
        if getattr(registry, 'debug_preds', False):
            _print_pred_debug('qualifying', stage, split_name, pipeline, y_true, preds, df)
        
        metrics = evaluate_regression(y_true, preds, df, 'qualifying')
        
        # Naive
        naive_preds = naive_qualifying_prediction(df)
        naive_metrics = evaluate_regression(y_true, naive_preds, df, 'qualifying_naive')
        naive_metrics = {f"{k}_naive" if not k.endswith('_naive') and k in ['mae', 'rmse'] else k: v for k, v in naive_metrics.items()}
        
        # Combine
        combined = {**metrics, **naive_metrics}
        registry.save_metrics(f'qualifying_{stage}', split_name, combined)
        
        # Verification print
        print(f"  Advanced {split_name} MAE: {metrics['mae']:.6f} | Naive {split_name} MAE: {naive_metrics.get('mae_naive', 'N/A')}")
        
    registry.save_model(pipeline, f'qualifying_advanced_{stage}')

def train_race_finish(stage, registry):
    print(f"Training Advanced Race Finish Model ({stage})...")
    features = pd.read_parquet("data/features/race_features.parquet")
    features = features[features['prediction_stage'] == stage]
    
    joined = load_and_join_data(features)
    joined = drop_missing_targets(joined, 'target_race_finish_position')
    
    train, val, test = time_based_split(joined)
    print(f"Data Splits -> Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    
    if train.empty:
        raise ValueError("No training data available after dropping missing targets.")
        
    y_train = train['target_race_finish_position']
    y_val = val['target_race_finish_position']
    y_test = test['target_race_finish_position']
    
    pipeline = get_baseline_pipeline(get_race_finish_advanced_model(), stage=stage)
    pipeline.fit(train, y_train)
    
    log_input_columns(pipeline, train, 'race_finish', stage, registry.debug_columns)
    
    for split_name, df, y_true in [('val', val, y_val), ('test', test, y_test)]:
        if df.empty:
            continue
        
        preds = pipeline.predict(df)
        
        if getattr(registry, 'debug_preds', False):
            _print_pred_debug('race_finish', stage, split_name, pipeline, y_true, preds, df)
        
        metrics = evaluate_regression(y_true, preds, df, 'race_finish')
        
        naive_func = naive_race_finish_pre_weekend if stage == 'pre_weekend' else naive_race_finish_post_qualifying
        naive_preds = naive_func(df)
        naive_metrics = evaluate_regression(y_true, naive_preds, df, 'race_finish_naive')
        naive_metrics = {f"{k}_naive" if not k.endswith('_naive') and k in ['mae', 'rmse'] else k: v for k, v in naive_metrics.items()}
        
        combined = {**metrics, **naive_metrics}
        registry.save_metrics(f'race_finish_{stage}', split_name, combined)
        
        # Verification print
        print(f"  Advanced {split_name} MAE: {metrics['mae']:.6f} | Naive {split_name} MAE: {naive_metrics.get('mae_naive', 'N/A')}")
        
    registry.save_model(pipeline, f'race_finish_advanced_{stage}')

def train_podium(stage, registry):
    print(f"Training Advanced Podium Classifier ({stage})...")
    features = pd.read_parquet("data/features/race_features.parquet")
    features = features[features['prediction_stage'] == stage]
    
    joined = load_and_join_data(features)
    joined = drop_missing_targets(joined, 'target_podium_class')
    
    # Binarize before splitting
    joined['target_podium_binary'] = joined['target_podium_class'].isin([1, 2, 3]).astype(int)
    
    train, val, test = time_based_split(joined)
    print(f"Data Splits -> Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    
    if train.empty:
        raise ValueError("No training data available after dropping missing targets.")
        
    y_train = train['target_podium_binary']
    y_val = val['target_podium_binary']
    y_test = test['target_podium_binary']
    
    if registry.debug_columns:
        print(f"\n[DEBUG] podium_{stage} Positive Rate -> Train: {y_train.mean():.3f} | Val: {y_val.mean():.3f} | Test: {y_test.mean():.3f}")
    
    pipeline = get_baseline_pipeline(get_podium_advanced_model(), stage=stage)
    pipeline.fit(train, y_train)
    
    log_input_columns(pipeline, train, 'podium', stage, registry.debug_columns)
    
    for split_name, df, y_true in [('val', val, y_val), ('test', test, y_test)]:
        if df.empty:
            continue
            
        preds = pipeline.predict(df)
        preds_proba = pipeline.predict_proba(df)[:, 1] if hasattr(pipeline, 'predict_proba') else preds
        metrics = evaluate_classification(y_true, preds_proba, preds, df, k=3)
        
        naive_func = naive_podium_pre_weekend if stage == 'pre_weekend' else naive_podium_post_qualifying
        naive_proba, naive_preds = naive_func(df)
        naive_metrics = evaluate_classification(y_true, naive_proba, naive_preds, df, k=3)
        naive_metrics = {f"{k}_naive": v for k, v in naive_metrics.items()}
        
        combined = {**metrics, **naive_metrics}
        registry.save_metrics(f'podium_{stage}', split_name, combined)
        
    registry.save_model(pipeline, f'podium_advanced_{stage}')

def train_top10(stage, registry):
    print(f"Training Advanced Top 10 Classifier ({stage})...")
    features = pd.read_parquet("data/features/race_features.parquet")
    features = features[features['prediction_stage'] == stage]
    
    joined = load_and_join_data(features)
    joined = drop_missing_targets(joined, 'target_top10')
    
    train, val, test = time_based_split(joined)
    print(f"Data Splits -> Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    
    if train.empty:
        raise ValueError("No training data available after dropping missing targets.")
        
    y_train = train['target_top10']
    y_val = val['target_top10']
    y_test = test['target_top10']
    
    if registry.debug_columns:
        print(f"\n[DEBUG] top10_{stage} Positive Rate -> Train: {y_train.mean():.3f} | Val: {y_val.mean():.3f} | Test: {y_test.mean():.3f}")
    
    pipeline = get_baseline_pipeline(get_top10_advanced_model(), stage=stage)
    pipeline.fit(train, y_train)
    
    log_input_columns(pipeline, train, 'top10', stage, registry.debug_columns)
    
    for split_name, df, y_true in [('val', val, y_val), ('test', test, y_test)]:
        if df.empty:
            continue
            
        preds = pipeline.predict(df)
        preds_proba = pipeline.predict_proba(df)[:, 1] if hasattr(pipeline, 'predict_proba') else preds
        metrics = evaluate_classification(y_true, preds_proba, preds, df, k=10)
        
        naive_func = naive_top10_pre_weekend if stage == 'pre_weekend' else naive_top10_post_qualifying
        naive_proba, naive_preds = naive_func(df)
        naive_metrics = evaluate_classification(y_true, naive_proba, naive_preds, df, k=10)
        naive_metrics = {f"{k}_naive": v for k, v in naive_metrics.items()}
        
        combined = {**metrics, **naive_metrics}
        registry.save_metrics(f'top10_{stage}', split_name, combined)
        
    registry.save_model(pipeline, f'top10_advanced_{stage}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=str, choices=["qualifying", "race_finish", "podium", "top10", "all"], default="all")
    parser.add_argument("--stage", type=str, choices=["pre_weekend", "post_qualifying", "all"], default="all")
    parser.add_argument("--debug-columns", action="store_true", help="Print debug info about columns and splits")
    parser.add_argument("--debug-preds", action="store_true", help="Print diagnostic prediction stats for regression tasks")
    args = parser.parse_args()
    
    tasks = ["qualifying", "race_finish", "podium", "top10"] if args.task == "all" else [args.task]
    stages = ["pre_weekend", "post_qualifying"] if args.stage == "all" else [args.stage]
    
    registry = ModelRegistry(
        models_dir="models/advanced",
        metrics_filename="advanced_metrics.json",
        predictions_filename="advanced_predictions.parquet"
    )
    registry.debug_columns = args.debug_columns
    registry.debug_preds = args.debug_preds
    
    for task in tasks:
        for stage in stages:
            if task == "qualifying" and stage != "pre_weekend":
                continue # Qualifying only has pre_weekend stage logically in our baseline
                
            if task == "qualifying":
                train_qualifying(stage, registry)
            elif task == "race_finish":
                train_race_finish(stage, registry)
            elif task == "podium":
                train_podium(stage, registry)
            elif task == "top10":
                train_top10(stage, registry)

    # Generate comparison if all done
    generate_model_comparison()

def generate_model_comparison():
    import json
    from pathlib import Path
    
    base_path = Path("reports/baseline_metrics.json")
    adv_path = Path("reports/advanced_metrics.json")
    out_path = Path("reports/model_comparison.json")
    
    if not base_path.exists() or not adv_path.exists():
        return
        
    with open(base_path, "r") as f:
        base_data = json.load(f)
    with open(adv_path, "r") as f:
        adv_data = json.load(f)
        
    comparison = {}
    
    for group in adv_data:
        if group in base_data:
            comparison[group] = {}
            for split in adv_data[group]:
                if split in base_data[group]:
                    comparison[group][split] = {}
                    for metric_name, adv_val in adv_data[group][split].items():
                        if not metric_name.endswith('_naive'):
                            base_val = base_data[group][split].get(metric_name)
                            if base_val is not None:
                                if metric_name in ['mae', 'rmse']:
                                    improved = adv_val < base_val
                                else:
                                    improved = adv_val > base_val
                                    
                                comparison[group][split][metric_name] = {
                                    'advanced': adv_val,
                                    'baseline': base_val,
                                    'improved': improved
                                }
                                
    with open(out_path, "w") as f:
        json.dump(comparison, f, indent=4)

if __name__ == "__main__":
    main()
