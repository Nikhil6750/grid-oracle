import pandas as pd
import numpy as np
from src.feature_engineering.driver_features import DriverFeatureBuilder
from src.feature_engineering.target_builder import TargetBuilder
from src.feature_engineering.weekend_features import WeekendFeatureBuilder
from src.feature_engineering.feature_store import FeatureStore

def test_driver_feature_builder_shifting():
    # Setup mock data for 3 races for 1 driver
    results = pd.DataFrame({
        'season': [2023, 2023, 2023],
        'round': [1, 2, 3],
        'event_name': ['Event 1', 'Event 2', 'Event 3'],
        'driver_code': ['VER', 'VER', 'VER'],
        'Position': [1, 2, 3],
        'Points': [25, 18, 15],
        'Status': ['Finished', 'Finished', 'Finished']
    })
    
    quali = pd.DataFrame({
        'season': [2023, 2023, 2023],
        'round': [1, 2, 3],
        'driver_code': ['VER', 'VER', 'VER'],
        'Position': [1, 1, 2]
    })
    
    builder = DriverFeatureBuilder(results, quali)
    features = builder.build_features()
    
    assert len(features) == 3
    
    # Check Race 1 (no previous history)
    race1 = features[(features['season'] == 2023) & (features['round'] == 1)].iloc[0]
    assert race1['driver_last_5_points_avg'] == 0.0
    assert race1['driver_last_5_points_avg_missing'] == 1
    
    # Check Race 2 (uses Race 1 only)
    race2 = features[(features['season'] == 2023) & (features['round'] == 2)].iloc[0]
    assert race2['driver_last_5_points_avg'] == 25.0 # Only race 1
    assert race2['driver_last_5_finish_avg'] == 1.0 # Only race 1
    assert race2['driver_last_5_points_avg_missing'] == 0
    
    # Check Race 3 (uses Race 1 and 2)
    race3 = features[(features['season'] == 2023) & (features['round'] == 3)].iloc[0]
    assert race3['driver_last_5_points_avg'] == (25 + 18) / 2
    assert race3['driver_season_points_before_event'] == 43.0
    
def test_target_builder():
    results = pd.DataFrame({
        'season': [2023, 2023, 2023, 2023],
        'round': [1, 1, 1, 1],
        'event_name': ['E', 'E', 'E', 'E'],
        'driver_code': ['A', 'B', 'C', 'D'],
        'driver_number': ['1', '2', '3', '4'],
        'Position': [1, 4, 11, pd.NA], # D is missing target
        'Points': [25, 12, 0, 0],
        'Status': ['Finished', 'Finished', 'Finished', 'Retired']
    })
    
    builder = TargetBuilder(results)
    targets = builder.build_targets()
    
    # Should drop driver D due to missing Position
    assert len(targets) == 3
    
    # Check A
    a = targets[targets['driver_code'] == 'A'].iloc[0]
    assert a['target_podium_class'] == 1
    assert a['target_top10'] == 1
    assert a['target_points_finish'] == 1
    assert a['target_dnf'] == 0
    
    # Check B
    b = targets[targets['driver_code'] == 'B'].iloc[0]
    assert b['target_podium_class'] == 4
    
    # Check C
    c = targets[targets['driver_code'] == 'C'].iloc[0]
    assert c['target_top10'] == 0
    assert c['target_points_finish'] == 0


def test_pre_weekend_has_no_same_weekend_columns():
    """pre_weekend rows must not contain same-weekend qualifying, sprint, or race columns."""
    results = pd.DataFrame({
        'season': [2023, 2023],
        'round': [1, 1],
        'event_name': ['Event 1', 'Event 1'],
        'driver_code': ['VER', 'HAM'],
        'driver_number': ['1', '44'],
        'team': ['Red Bull', 'Mercedes'],
        'Position': [1, 2],
        'Points': [25, 18],
        'Status': ['Finished', 'Finished']
    })

    driver_builder = DriverFeatureBuilder(results)
    from src.feature_engineering.team_features import TeamFeatureBuilder
    team_builder = TeamFeatureBuilder(results)
    
    driver_feats = driver_builder.build_features()
    team_feats = team_builder.build_features()

    wb = WeekendFeatureBuilder(driver_feats, team_feats, pd.DataFrame())
    pre_weekend = wb.build_pre_weekend(results, pd.DataFrame())

    forbidden = [
        'qualifying_position', 'qualifying_gap_to_pole', 'teammate_qualifying_delta',
        'sprint_position', 'sprint_points', 'race_result', 'race_points',
    ]
    for col in forbidden:
        assert col not in pre_weekend.columns, f"Forbidden column {col} found in pre_weekend"
    
    assert 'prediction_stage' in pre_weekend.columns
    assert (pre_weekend['prediction_stage'] == 'pre_weekend').all()
    assert 'feature_source_sessions' in pre_weekend.columns
    assert (pre_weekend['feature_source_sessions'] == 'historical_only').all()


def test_pre_weekend_rows_are_generated():
    """Feature builder must create pre_weekend rows for every driver/race."""
    results = pd.DataFrame({
        'season': [2023, 2023, 2023, 2023],
        'round': [1, 1, 2, 2],
        'event_name': ['Event 1', 'Event 1', 'Event 2', 'Event 2'],
        'driver_code': ['VER', 'HAM', 'VER', 'HAM'],
        'driver_number': ['1', '44', '1', '44'],
        'team': ['Red Bull', 'Mercedes', 'Red Bull', 'Mercedes'],
        'Position': [1, 2, 2, 1],
        'Points': [25, 18, 18, 25],
        'Status': ['Finished', 'Finished', 'Finished', 'Finished']
    })
    
    driver_feats = DriverFeatureBuilder(results).build_features()
    from src.feature_engineering.team_features import TeamFeatureBuilder
    team_feats = TeamFeatureBuilder(results).build_features()

    wb = WeekendFeatureBuilder(driver_feats, team_feats, pd.DataFrame())
    pre_weekend = wb.build_pre_weekend(results, pd.DataFrame())

    # Should have 4 rows: 2 drivers x 2 rounds
    assert len(pre_weekend) == 4
    assert set(pre_weekend['prediction_stage'].unique()) == {'pre_weekend'}


def test_missing_indicator_columns_contain_no_nulls():
    """Every *_missing column must contain only 0 or 1, never null."""
    results = pd.DataFrame({
        'season': [2023, 2023],
        'round': [1, 1],
        'event_name': ['Event 1', 'Event 1'],
        'driver_code': ['VER', 'HAM'],
        'driver_number': ['1', '44'],
        'team': ['Red Bull', 'Mercedes'],
        'Position': [1, 2],
        'Points': [25, 18],
        'Status': ['Finished', 'Finished']
    })

    driver_feats = DriverFeatureBuilder(results).build_features()
    from src.feature_engineering.team_features import TeamFeatureBuilder
    team_feats = TeamFeatureBuilder(results).build_features()

    wb = WeekendFeatureBuilder(driver_feats, team_feats, pd.DataFrame())
    pre_weekend = wb.build_pre_weekend(results, pd.DataFrame())
    post_qualifying = wb.build_post_qualifying(pre_weekend, pd.DataFrame())

    # Check all _missing columns in post_qualifying (no Q data = imputed)
    missing_cols = [c for c in post_qualifying.columns if c.endswith('_missing')]
    assert len(missing_cols) > 0, "Expected some _missing columns"
    for col in missing_cols:
        assert post_qualifying[col].isna().sum() == 0, f"{col} contains null values"
        assert set(post_qualifying[col].unique()).issubset({0, 1}), f"{col} contains values other than 0/1"


def test_race_features_sprint_missing_indicators_no_nulls():
    """For non-sprint race features, sprint_*_missing must be 1 (not null)."""
    results = pd.DataFrame({
        'season': [2023, 2023],
        'round': [1, 1],
        'event_name': ['Event 1', 'Event 1'],
        'driver_code': ['VER', 'HAM'],
        'driver_number': ['1', '44'],
        'team': ['Red Bull', 'Mercedes'],
        'Position': [1, 2],
        'Points': [25, 18],
        'Status': ['Finished', 'Finished']
    })

    driver_feats = DriverFeatureBuilder(results).build_features()
    from src.feature_engineering.team_features import TeamFeatureBuilder
    team_feats = TeamFeatureBuilder(results).build_features()

    wb = WeekendFeatureBuilder(driver_feats, team_feats, pd.DataFrame())
    pre_weekend = wb.build_pre_weekend(results, pd.DataFrame())
    post_qualifying = wb.build_post_qualifying(pre_weekend, pd.DataFrame())

    # Build race_features for non-sprint (sprint_weekend_flag == 0)
    store = FeatureStore.__new__(FeatureStore)
    race_features = post_qualifying[post_qualifying['sprint_weekend_flag'] == 0].copy()
    race_features = store._ensure_sprint_columns(race_features)
    race_features = store._fix_all_missing_indicators(race_features)

    assert 'sprint_position_missing' in race_features.columns
    assert race_features['sprint_position_missing'].isna().sum() == 0
    assert (race_features['sprint_position_missing'] == 1).all()
    assert 'sprint_points_missing' in race_features.columns
    assert (race_features['sprint_points_missing'] == 1).all()


def test_race_features_contains_pre_weekend():
    """race_features must contain pre_weekend rows, properly imputed with missing indicators for same-weekend data."""
    results = pd.DataFrame({
        'season': [2023, 2023],
        'round': [1, 1],
        'event_name': ['Event 1', 'Event 1'],
        'driver_code': ['VER', 'HAM'],
        'driver_number': ['1', '44'],
        'team': ['Red Bull', 'Mercedes'],
        'Position': [1, 2],
        'Points': [25, 18],
        'Status': ['Finished', 'Finished']
    })

    driver_feats = DriverFeatureBuilder(results).build_features()
    from src.feature_engineering.team_features import TeamFeatureBuilder
    team_feats = TeamFeatureBuilder(results).build_features()

    wb = WeekendFeatureBuilder(driver_feats, team_feats, pd.DataFrame())
    pre_weekend = wb.build_pre_weekend(results, pd.DataFrame())
    post_qualifying = wb.build_post_qualifying(pre_weekend, pd.DataFrame())

    store = FeatureStore.__new__(FeatureStore)
    race_features_parts = [pre_weekend, post_qualifying]
    race_features = pd.concat(race_features_parts, ignore_index=True)
    
    race_features = store._ensure_qualifying_columns(race_features)
    race_features = store._ensure_sprint_columns(race_features)
    race_features = store._fix_all_missing_indicators(race_features)

    # 1. Contains pre_weekend rows
    assert 'pre_weekend' in race_features['prediction_stage'].values
    
    pre_weekend_rows = race_features[race_features['prediction_stage'] == 'pre_weekend']
    
    # 2. No same-weekend columns (meaning they are missing=1)
    assert (pre_weekend_rows['qualifying_position_missing'] == 1).all()
    assert (pre_weekend_rows['sprint_position_missing'] == 1).all()
    
    # 3. Source session is historical_only
    assert (pre_weekend_rows['feature_source_sessions'] == 'historical_only').all()
