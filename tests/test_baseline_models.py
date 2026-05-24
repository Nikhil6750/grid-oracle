import pandas as pd
import numpy as np
from src.modeling.preprocessing import get_baseline_pipeline
from src.modeling.baseline_models import get_qualifying_model
from src.modeling.evaluation import evaluate_regression

def test_tiny_model_pipeline_fit_predict():
    """Test that the model pipeline can fit and predict on a tiny sample without target columns or IDs in X."""
    df = pd.DataFrame({
        'season': [2023, 2023, 2023],
        'round': [1, 1, 1],
        'event_name': ['Event 1', 'Event 1', 'Event 1'],
        'driver_number': ['1', '44', '16'],
        'driver_code': ['VER', 'HAM', 'LEC'],
        'team': ['Red Bull', 'Mercedes', 'Ferrari'],
        'prediction_stage': ['pre_weekend', 'pre_weekend', 'pre_weekend'],
        'feature_cutoff_stage': ['pre_weekend', 'pre_weekend', 'pre_weekend'],
        'track_type': ['Street', 'Street', 'Street'],
        'tyre_degradation_category': ['Medium', 'Medium', 'Medium'],
        'driver_last_5_points_avg': [25.0, 18.0, np.nan],
        'target_qualifying_position': [1, 2, 3]
    })
    
    y = df['target_qualifying_position']
    
    # Assert driver_code and targets are in df before pipeline
    assert 'driver_code' in df.columns
    assert 'target_qualifying_position' in df.columns
    
    pipeline = get_baseline_pipeline(get_qualifying_model(), stage='pre_weekend')
    
    # fit
    pipeline.fit(df, y)
    
    # Check the preprocessor's drop list
    preprocessor = pipeline.named_steps['preprocessor']
    assert 'driver_code' in preprocessor.drop_features
    assert 'driver_number' in preprocessor.drop_features
    assert 'target_qualifying_position' in preprocessor.drop_features
    
    # predict
    preds = pipeline.predict(df)
    assert len(preds) == 3
    
    # evaluate metrics schema
    metrics = evaluate_regression(y.values, preds, df, 'test_task')
    assert 'mae' in metrics
    assert 'rmse' in metrics
    assert 'test_task_top1_accuracy' in metrics

def test_pipeline_serialization(tmp_path):
    """Test that the custom pipeline (with DynamicPreprocessor) can be serialized and deserialized using joblib."""
    import joblib
    
    df = pd.DataFrame({
        'season': [2023, 2023],
        'driver_code': ['VER', 'HAM'],
        'team': ['Red Bull', 'Mercedes'],
        'driver_last_5_points_avg': [25.0, 18.0],
        'target_qualifying_position': [1, 2]
    })
    
    y = df['target_qualifying_position']
    pipeline = get_baseline_pipeline(get_qualifying_model(), stage='pre_weekend')
    pipeline.fit(df, y)
    
    # Save
    model_path = tmp_path / "test_model.joblib"
    joblib.dump(pipeline, model_path)
    
    # Load
    loaded_pipeline = joblib.load(model_path)
    
    # Predict
    preds = loaded_pipeline.predict(df)
    assert len(preds) == 2

def test_leakage_guard():
    from src.modeling.preprocessing import LeakageGuard
    import pytest
    
    # Valid
    df_valid = pd.DataFrame({'driver_last_5_finish_avg': [2.5]})
    guard = LeakageGuard(stage='pre_weekend')
    guard.fit(df_valid) # should not raise
    
    # Target injection
    df_invalid = pd.DataFrame({'target_podium_class': [1]})
    with pytest.raises(ValueError, match="Leakage detected"):
        guard.fit(df_invalid)
        
    df_invalid2 = pd.DataFrame({'race_finish_position': [1]})
    with pytest.raises(ValueError, match="Leakage detected"):
        guard.fit(df_invalid2)
        
    # Exception check: qualifying_position in pre_weekend -> raises
    df_invalid3 = pd.DataFrame({'qualifying_position': [1]})
    with pytest.raises(ValueError, match="Leakage detected: 'qualifying_position' found in stage 'pre_weekend'"):
        guard.fit(df_invalid3)
        
    # Exception check: qualifying_position in post_qualifying -> passes
    guard2 = LeakageGuard(stage='post_qualifying')
    guard2.fit(df_invalid3) # should pass

def test_evaluation_metrics():
    from src.modeling.evaluation import evaluate_classification
    
    # 2 races, 4 drivers each
    df = pd.DataFrame({
        'season': [2023]*8,
        'round': [1]*4 + [2]*4,
        'driver_code': ['A', 'B', 'C', 'D', 'A', 'B', 'C', 'D']
    })
    
    # True: A, B, C are podium
    y_true = np.array([1, 1, 1, 0, 1, 1, 1, 0])
    
    # Perfect predictions
    y_pred_perf = np.array([1, 1, 1, 0, 1, 1, 1, 0])
    y_proba_perf = np.array([0.9, 0.8, 0.7, 0.1, 0.9, 0.8, 0.7, 0.1])
    
    metrics_perf = evaluate_classification(y_true, y_proba_perf, y_pred_perf, df, k=3)
    assert metrics_perf['roc_auc'] == 1.0
    assert metrics_perf['top3_accuracy'] == 1.0
    
    # Noisy predictions (D is predicted best, C is predicted worst)
    y_pred_noise = np.array([1, 1, 0, 1, 1, 1, 0, 1])
    y_proba_noise = np.array([0.8, 0.7, 0.1, 0.9, 0.8, 0.7, 0.1, 0.9])
    
    metrics_noise = evaluate_classification(y_true, y_proba_noise, y_pred_noise, df, k=3)
    
    # AUC should be imperfect
    assert metrics_noise['roc_auc'] < 1.0
    assert metrics_noise['pr_auc'] < 1.0
    assert metrics_noise['precision'] < 1.0
    
    # Top 3 should be D, A, B. Actual top 3 are A, B, C. Intersection = A, B (2 out of 3 = 0.66)
    assert 0.6 < metrics_noise['top3_accuracy'] < 0.7

def test_stage_feature_dropper():
    from src.modeling.preprocessing import StageFeatureDropper
    
    df = pd.DataFrame({
        'driver_last_5_finish_avg': [2.5],
        'qualifying_position': [1],
        'sprint_points': [8],
        'team_qualifying_rank': [1]
    })
    
    # Pre-weekend drops everything except the general history
    pre_dropper = StageFeatureDropper(stage='pre_weekend')
    pre_dropped = pre_dropper.fit_transform(df)
    assert 'qualifying_position' not in pre_dropped.columns
    assert 'sprint_points' not in pre_dropped.columns
    assert 'team_qualifying_rank' not in pre_dropped.columns
    assert 'driver_last_5_finish_avg' in pre_dropped.columns
    
    # Post-qualifying keeps qualifying but drops sprint
    post_dropper = StageFeatureDropper(stage='post_qualifying')
    post_dropped = post_dropper.fit_transform(df)
    assert 'qualifying_position' in post_dropped.columns
    assert 'team_qualifying_rank' in post_dropped.columns
    assert 'sprint_points' not in post_dropped.columns
    assert 'driver_last_5_finish_avg' in post_dropped.columns

def test_debug_log_input_columns(tmp_path):
    from scripts.train_baselines import log_input_columns
    from src.modeling.preprocessing import get_baseline_pipeline
    from src.modeling.baseline_models import get_qualifying_model
    import json
    import os
    
    # Mock data
    df = pd.DataFrame({
        'season': [2023, 2023],
        'driver_code': ['VER', 'HAM'],
        'team': ['Red Bull', 'Mercedes'],
        'driver_last_5_points_avg': [25.0, 18.0],
        'qualifying_position': [1, 2],
        'sprint_points': [8, 7],
        'target_qualifying_position': [1, 2]
    })
    
    y = df['target_qualifying_position']
    pipeline = get_baseline_pipeline(get_qualifying_model(), stage='pre_weekend')
    pipeline.fit(df, y)
    
    # Redirect output to tmp for reports/model_input_columns.json
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        log_input_columns(pipeline, df, 'qualifying', 'pre_weekend', debug=True)
        
        with open("reports/model_input_columns.json", "r") as f:
            data = json.load(f)
            
        used = data['qualifying_pre_weekend']
        assert 'driver_last_5_points_avg' in used
        assert 'team' in used
        assert 'qualifying_position' not in used
        assert 'sprint_points' not in used
        assert 'target_qualifying_position' not in used
        assert 'driver_code' not in used
    finally:
        os.chdir(original_cwd)
