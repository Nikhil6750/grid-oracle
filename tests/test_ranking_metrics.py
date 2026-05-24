import pandas as pd
import numpy as np
from src.modeling.ranking import rank_drivers_by_prediction, get_top_k_ranked_drivers

def test_rank_drivers_by_prediction():
    """Verify ranking assigns correctly per race (descending score)."""
    df = pd.DataFrame({
        'season': [2023, 2023, 2023, 2024],
        'round': [1, 1, 1, 1],
        'driver_code': ['A', 'B', 'C', 'A']
    })
    
    # B is best in 2023 R1, C is worst. A is best in 2024 R1
    preds = np.array([0.5, 0.9, 0.1, 0.8])
    
    ranked = rank_drivers_by_prediction(df, preds, descending=True)
    
    # B should be rank 1
    assert ranked.loc[ranked['driver_code'] == 'B', 'predicted_rank'].values[0] == 1
    # A should be rank 2
    assert ranked.loc[(ranked['driver_code'] == 'A') & (ranked['season'] == 2023), 'predicted_rank'].values[0] == 2
    # C should be rank 3
    assert ranked.loc[ranked['driver_code'] == 'C', 'predicted_rank'].values[0] == 3
    
    # 2024 race
    assert ranked.loc[(ranked['driver_code'] == 'A') & (ranked['season'] == 2024), 'predicted_rank'].values[0] == 1

def test_rank_drivers_ascending():
    """Verify ranking assigns correctly per race (ascending score like race finish)."""
    df = pd.DataFrame({
        'season': [2023, 2023, 2023],
        'round': [1, 1, 1],
        'driver_code': ['A', 'B', 'C']
    })
    
    # B is predicted to finish 1st, A 5th, C 20th
    preds = np.array([5, 1, 20])
    
    ranked = rank_drivers_by_prediction(df, preds, descending=False)
    
    assert ranked.loc[ranked['driver_code'] == 'B', 'predicted_rank'].values[0] == 1
    assert ranked.loc[ranked['driver_code'] == 'A', 'predicted_rank'].values[0] == 2
    assert ranked.loc[ranked['driver_code'] == 'C', 'predicted_rank'].values[0] == 3

def test_get_top_k_ranked_drivers():
    """Verify slicing top K works correctly."""
    df = pd.DataFrame({
        'season': [2023, 2023, 2023],
        'round': [1, 1, 1],
        'driver_code': ['A', 'B', 'C'],
        'predicted_rank': [2, 1, 3]
    })
    
    top2 = get_top_k_ranked_drivers(df, 2)
    assert len(top2) == 2
    assert 'C' not in top2['driver_code'].values
