import pandas as pd
import numpy as np
from src.modeling.data import load_and_join_data, time_based_split

def test_full_join_key_integrity_and_no_row_expansion():
    """Test full join key integrity and that the join does not expand rows."""
    features_df = pd.DataFrame({
        'season': [2023, 2023],
        'round': [1, 1],
        'event_name': ['Event 1', 'Event 1'],
        'driver_number': ['1', '44'],
        'driver_code': ['VER', 'HAM'],
        'prediction_stage': ['pre_weekend', 'pre_weekend'],
        'feature_1': [10.5, 9.2]
    })
    
    targets_df = pd.DataFrame({
        'season': [2023, 2023],
        'round': [1, 1],
        'event_name': ['Event 1', 'Event 1'],
        'driver_number': ['1', '44'],
        'driver_code': ['VER', 'HAM'],
        'prediction_stage': ['some_other_stage', 'some_other_stage'], # should be ignored
        'target_race_finish_position': [1, 2]
    })
    
    # Save dummy targets to a temporary file for the test
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        targets_df.to_parquet(tmp.name)
        
        joined = load_and_join_data(features_df, targets_path=tmp.name)
        
        # Test no row expansion
        assert len(joined) == len(features_df)
        
        # Test preservation of feature's prediction_stage
        assert all(joined['prediction_stage'] == 'pre_weekend')
        
        # Test targets are attached
        assert 'target_race_finish_position' in joined.columns
        assert joined.loc[joined['driver_code'] == 'VER', 'target_race_finish_position'].iloc[0] == 1

def test_time_split():
    """Test that time_based_split correctly partitions by year."""
    df = pd.DataFrame({
        'season': [2018, 2020, 2022, 2023, 2024, 2025],
        'data': [1, 2, 3, 4, 5, 6]
    })
    
    train, val, test = time_based_split(df)
    
    assert len(train) == 3
    assert set(train['season'].unique()) == {2018, 2020, 2022}
    
    assert len(val) == 1
    assert set(val['season'].unique()) == {2023}
    
    assert len(test) == 1
    assert set(test['season'].unique()) == {2024}

def test_drop_missing_targets():
    """Test that drop_missing_targets properly drops rows and raises error on empty remaining."""
    from src.modeling.data import drop_missing_targets
    df = pd.DataFrame({
        'season': [2023, 2023],
        'driver_code': ['VER', 'HAM'],
        'target_qualifying_position': [1.0, np.nan]
    })
    
    filtered = drop_missing_targets(df, 'target_qualifying_position')
    
    assert len(filtered) == 1
    assert filtered['driver_code'].iloc[0] == 'VER'
    assert not filtered['target_qualifying_position'].isna().any()
    
    # Test error on zero rows
    df_all_nan = pd.DataFrame({
        'target_qualifying_position': [np.nan, np.nan]
    })
    
    import pytest
    with pytest.raises(ValueError, match="Zero rows remaining"):
        drop_missing_targets(df_all_nan, 'target_qualifying_position')
