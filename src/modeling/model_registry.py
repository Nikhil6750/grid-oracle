import json
import joblib
from pathlib import Path
import pandas as pd

class ModelRegistry:
    def __init__(self, models_dir: str = "models/baseline", reports_dir: str = "reports", metrics_filename: str = "baseline_metrics.json", predictions_filename: str = "baseline_predictions.parquet"):
        self.models_dir = Path(models_dir)
        self.reports_dir = Path(reports_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_path = self.reports_dir / metrics_filename
        self.predictions_filename = predictions_filename
        
    def save_model(self, model, name: str):
        path = self.models_dir / f"{name}.joblib"
        joblib.dump(model, path)
        return str(path)
        
    def load_model(self, name: str):
        path = self.models_dir / f"{name}.joblib"
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {path}")
        return joblib.load(path)
        
    def save_metrics(self, group: str, split: str, metrics: dict):
        if self.metrics_path.exists():
            with open(self.metrics_path, "r") as f:
                all_metrics = json.load(f)
        else:
            all_metrics = {}
            
        if group not in all_metrics:
            all_metrics[group] = {}
        all_metrics[group][split] = metrics
        
        with open(self.metrics_path, "w") as f:
            json.dump(all_metrics, f, indent=4)
            
    def append_predictions(self, preds_df: pd.DataFrame):
        path = self.reports_dir / self.predictions_filename
        if path.exists():
            existing = pd.read_parquet(path)
            # Remove existing rows for the same combination of keys and stage
            if not preds_df.empty:
                keys = ['season', 'round', 'driver_code', 'prediction_stage']
                merged = pd.merge(existing, preds_df[keys], on=keys, how='outer', indicator=True)
                existing = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])
                combined = pd.concat([existing, preds_df], ignore_index=True)
        else:
            combined = preds_df
            
        combined.to_parquet(path)
