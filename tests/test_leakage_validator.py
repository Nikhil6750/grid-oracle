import pandas as pd
from src.feature_engineering.leakage_validator import LeakageValidator

def test_leakage_validator_catches_target_in_features():
    targets = pd.DataFrame({'season': [2023], 'round': [1], 'driver_code': ['VER'], 'target_race_finish_position': [1]})
    
    # Leaky q_features
    q_features = pd.DataFrame({
        'season': [2023], 'round': [1], 'driver_code': ['VER'], 
        'prediction_stage': ['pre_weekend'],
        'feature_source_sessions': ['historical'],
        'feature_cutoff_stage': ['pre_weekend'],
        'driver_last_5_finish_avg': [1.0],
        'target_race_finish_position': [1] # LEAKAGE!
    })
    
    r_features = pd.DataFrame()
    s_features = pd.DataFrame()
    
    validator = LeakageValidator(targets, q_features, r_features, s_features)
    is_valid = validator.validate()
    
    assert not is_valid
    assert len(validator.errors) > 0
    assert "target_race_finish_position" in validator.errors[0]
    
def test_leakage_validator_catches_race_in_q_features():
    targets = pd.DataFrame({'season': [2023], 'round': [1], 'driver_code': ['VER']})
    
    q_features = pd.DataFrame({
        'season': [2023], 'round': [1], 'driver_code': ['VER'], 
        'prediction_stage': ['post_qualifying'],
        'feature_source_sessions': ['Q'],
        'feature_cutoff_stage': ['post_qualifying'],
        'driver_last_5_finish_avg': [1.0],
        'race_points': [25] # LEAKAGE!
    })
    
    validator = LeakageValidator(targets, q_features, pd.DataFrame(), pd.DataFrame())
    assert not validator.validate()
    assert any("Race derived column" in err for err in validator.errors)
    
def test_leakage_validator_catches_missing_meta():
    targets = pd.DataFrame({'season': [2023], 'round': [1], 'driver_code': ['VER']})
    
    q_features = pd.DataFrame({
        'season': [2023], 'round': [1], 'driver_code': ['VER'], 
        'driver_last_5_finish_avg': [1.0]
        # Missing feature_source_sessions
    })
    
    validator = LeakageValidator(targets, q_features, pd.DataFrame(), pd.DataFrame())
    assert not validator.validate()
    assert any("Missing feature_source_sessions" in err for err in validator.errors)
    
def test_leakage_validator_passes_valid_data():
    targets = pd.DataFrame({
        'season': [2023], 'round': [1], 'driver_code': ['VER'],
        'target_race_finish_position': [1]
    })
    
    q_features = pd.DataFrame({
        'season': [2023], 'round': [1], 'driver_code': ['VER'], 
        'prediction_stage': ['pre_weekend'],
        'feature_source_sessions': ['historical'],
        'feature_cutoff_stage': ['pre_weekend'],
        'driver_last_5_finish_avg': [1.0]
    })
    
    validator = LeakageValidator(targets, q_features, pd.DataFrame(), pd.DataFrame())
    assert validator.validate()
    assert len(validator.errors) == 0


def test_leakage_validator_catches_qualifying_in_pre_weekend():
    """pre_weekend (qualifying_features) must not contain same-weekend qualifying columns."""
    targets = pd.DataFrame({'season': [2023], 'round': [1], 'driver_code': ['VER']})
    
    q_features = pd.DataFrame({
        'season': [2023], 'round': [1], 'driver_code': ['VER'],
        'prediction_stage': ['pre_weekend'],
        'feature_source_sessions': ['historical'],
        'feature_cutoff_stage': ['pre_weekend'],
        'driver_last_5_finish_avg': [1.0],
        'qualifying_position': [1],  # LEAKAGE — same-weekend Q data in pre_weekend
    })
    
    validator = LeakageValidator(targets, q_features, pd.DataFrame(), pd.DataFrame())
    assert not validator.validate()
    assert any("Rule 2" in err for err in validator.errors)


def test_leakage_validator_missing_indicators_no_nulls():
    """*_missing columns with null values should fail validation."""
    targets = pd.DataFrame({'season': [2023], 'round': [1], 'driver_code': ['VER'],
                            'target_race_finish_position': [1]})
    
    r_features = pd.DataFrame({
        'season': [2023], 'round': [1], 'driver_code': ['VER'],
        'prediction_stage': ['post_qualifying'],
        'feature_source_sessions': ['historical,Q'],
        'feature_cutoff_stage': ['post_qualifying'],
        'driver_last_5_finish_avg': [1.0],
        'sprint_position_missing': [pd.NA],  # Null in _missing column!
    })
    
    validator = LeakageValidator(targets, pd.DataFrame(), r_features, pd.DataFrame())
    assert not validator.validate()
    assert any("Rule 11" in err for err in validator.errors)
