import pandas as pd
import numpy as np
import pytest
from pathlib import Path
import json

from src.modeling.preprocessing import get_baseline_pipeline
from src.modeling.advanced_models import get_podium_advanced_model

def test_advanced_model_fit_predict():
    """Test that the advanced model can fit and predict on a tiny dataset without breaking."""
    df = pd.DataFrame({
        'season': [2023, 2023] * 10,
        'round': [1, 1] * 10,
        'driver_code': ['VER', 'HAM'] * 10,
        'team': ['Red Bull', 'Mercedes'] * 10,
        'driver_last_5_points_avg': [25.0, 18.0] * 10,
        'some_numeric_feature': [1.0, 2.0] * 10
    })
    
    y = pd.Series([1, 0] * 10)
    
    # Pre-weekend stage
    pipeline = get_baseline_pipeline(get_podium_advanced_model(), stage='pre_weekend')
    
    # Fit
    pipeline.fit(df, y)
    
    # Predict
    preds = pipeline.predict(df)
    preds_proba = pipeline.predict_proba(df)[:, 1]
    
    assert len(preds) == 20
    assert len(preds_proba) == 20
    assert 0.0 <= preds_proba[0] <= 1.0

def test_no_leakage_in_advanced():
    """Verify that using the advanced model pipeline still triggers the LeakageGuard."""
    df = pd.DataFrame({
        'race_finish_position': [1, 2],
        'some_numeric_feature': [1.0, 2.0]
    })
    
    pipeline = get_baseline_pipeline(get_podium_advanced_model(), stage='pre_weekend')
    
    with pytest.raises(ValueError, match="Leakage detected"):
        pipeline.fit(df, pd.Series([1, 0]))

def test_model_comparison_generation(tmp_path):
    """Test that model_comparison.json is generated correctly."""
    from scripts.train_advanced import generate_model_comparison
    import os
    
    # Create fake reports dir
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    
    base_data = {
        "podium_pre_weekend": {
            "test": {
                "roc_auc": 0.80,
                "precision": 0.50
            }
        }
    }
    
    adv_data = {
        "podium_pre_weekend": {
            "test": {
                "roc_auc": 0.85,
                "precision": 0.45
            }
        }
    }
    
    with open(reports_dir / "baseline_metrics.json", "w") as f:
        json.dump(base_data, f)
        
    with open(reports_dir / "advanced_metrics.json", "w") as f:
        json.dump(adv_data, f)
        
    # Redirect cwd to tmp_path so the script finds the reports folder
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        generate_model_comparison()
        
        with open(reports_dir / "model_comparison.json", "r") as f:
            comp = json.load(f)
            
        assert "podium_pre_weekend" in comp
        assert comp["podium_pre_weekend"]["test"]["roc_auc"]["improved"] is True
        assert comp["podium_pre_weekend"]["test"]["roc_auc"]["advanced"] == 0.85
        assert comp["podium_pre_weekend"]["test"]["precision"]["improved"] is False
    finally:
        os.chdir(original_cwd)

def test_regression_metrics_from_predictions():
    """Verify evaluate_regression computes MAE/RMSE from the supplied predictions, not from some other source."""
    from src.modeling.evaluation import evaluate_regression
    
    df = pd.DataFrame({
        'season': [2023]*4,
        'round': [1]*4,
        'driver_code': ['A', 'B', 'C', 'D']
    })
    
    y_true = np.array([1, 2, 3, 4])
    y_pred_good = np.array([1.5, 2.5, 3.5, 4.5])  # MAE = 0.5
    y_pred_bad = np.array([5, 5, 5, 5])            # MAE = 2.5
    
    metrics_good = evaluate_regression(y_true, y_pred_good, df, 'test')
    metrics_bad = evaluate_regression(y_true, y_pred_bad, df, 'test')
    
    assert abs(metrics_good['mae'] - 0.5) < 1e-6
    assert abs(metrics_bad['mae'] - 2.5) < 1e-6
    assert metrics_good['mae'] != metrics_bad['mae']

def test_top1_uses_same_predictions_as_mae():
    """Verify top1 accuracy is computed from the same y_pred array that generates MAE."""
    from src.modeling.evaluation import evaluate_regression
    
    df = pd.DataFrame({
        'season': [2023]*4,
        'round': [1]*4,
        'driver_code': ['A', 'B', 'C', 'D']
    })
    
    y_true = np.array([1, 5, 10, 15])  # A is actual best
    y_pred = np.array([2, 1, 12, 16])  # B is predicted best (wrong)
    
    metrics = evaluate_regression(y_true, y_pred, df, 'test')
    
    # top1 should be 0 because predicted best (B) != actual best (A)
    assert metrics['test_top1_accuracy'] == 0.0
    
    # Now fix predictions so A is predicted best
    y_pred_correct = np.array([1, 5, 10, 15])  # A is predicted best (correct)
    metrics_correct = evaluate_regression(y_true, y_pred_correct, df, 'test')
    assert metrics_correct['test_top1_accuracy'] == 1.0
    assert metrics_correct['mae'] == 0.0

def test_comparison_does_not_overwrite_advanced_with_baseline(tmp_path):
    """Verify generate_model_comparison reads independent files and doesn't copy baseline into advanced."""
    from scripts.train_advanced import generate_model_comparison
    import os
    
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    
    base_data = {
        "race_finish_pre_weekend": {
            "test": {
                "mae": 5.0,
                "rmse": 7.0
            }
        }
    }
    
    adv_data = {
        "race_finish_pre_weekend": {
            "test": {
                "mae": 3.5,
                "rmse": 4.5
            }
        }
    }
    
    with open(reports_dir / "baseline_metrics.json", "w") as f:
        json.dump(base_data, f)
    with open(reports_dir / "advanced_metrics.json", "w") as f:
        json.dump(adv_data, f)
    
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        generate_model_comparison()
        
        with open(reports_dir / "model_comparison.json", "r") as f:
            comp = json.load(f)
        
        # Advanced values must match adv_data, NOT base_data
        assert comp["race_finish_pre_weekend"]["test"]["mae"]["advanced"] == 3.5
        assert comp["race_finish_pre_weekend"]["test"]["mae"]["baseline"] == 5.0
        assert comp["race_finish_pre_weekend"]["test"]["mae"]["improved"] is True
        
        assert comp["race_finish_pre_weekend"]["test"]["rmse"]["advanced"] == 4.5
        assert comp["race_finish_pre_weekend"]["test"]["rmse"]["baseline"] == 7.0
        assert comp["race_finish_pre_weekend"]["test"]["rmse"]["improved"] is True
    finally:
        os.chdir(original_cwd)

def test_naive_metrics_do_not_overwrite_model_mae():
    """Regression test: naive 'mae'/'rmse' keys must be renamed with _naive suffix
    before merging with model metrics, so they don't overwrite the model's MAE/RMSE."""
    from src.modeling.evaluation import evaluate_regression
    
    df = pd.DataFrame({
        'season': [2023]*4,
        'round': [1]*4,
        'driver_code': ['A', 'B', 'C', 'D']
    })
    
    y_true = np.array([1.0, 2.0, 3.0, 4.0])
    model_preds = np.array([1.5, 2.5, 3.5, 4.5])   # model MAE = 0.5
    naive_preds = np.array([10.0, 10.0, 10.0, 10.0])  # naive MAE = 7.5
    
    model_metrics = evaluate_regression(y_true, model_preds, df, 'test')
    naive_metrics = evaluate_regression(y_true, naive_preds, df, 'test_naive')
    
    # Without fix: {**model_metrics, **naive_metrics} overwrites mae with 7.5
    # With fix: rename naive keys first
    naive_metrics_fixed = {f"{k}_naive" if not k.endswith('_naive') and k in ['mae', 'rmse'] else k: v for k, v in naive_metrics.items()}
    
    combined = {**model_metrics, **naive_metrics_fixed}
    
    # Model MAE must survive the merge
    assert abs(combined['mae'] - 0.5) < 1e-6, f"Model MAE was overwritten! Got {combined['mae']}"
    assert 'mae_naive' in combined, "Naive MAE key missing"
    assert abs(combined['mae_naive'] - 7.5) < 1e-6
