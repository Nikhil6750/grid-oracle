import pandas as pd
from pathlib import Path

def load_and_join_data(features_df: pd.DataFrame, targets_path: str = "data/features/targets.parquet") -> pd.DataFrame:
    """Joins features with targets, preserving prediction_stage from features."""
    if features_df.empty:
        return pd.DataFrame()
        
    targets_df = pd.read_parquet(targets_path)
    if targets_df.empty:
        return features_df
        
    # Keys for join
    join_keys = ['season', 'round', 'driver_code']
    
    # Check if 'event_name' and 'driver_number' are in targets, if so use them as well
    for k in ['event_name', 'driver_number']:
        if k in targets_df.columns and k in features_df.columns:
            join_keys.append(k)
            
    # If targets contains prediction_stage, drop it before join so we keep feature's stage
    if 'prediction_stage' in targets_df.columns:
        targets_df = targets_df.drop(columns=['prediction_stage'])
        
    # Perform inner join
    joined_df = pd.merge(features_df, targets_df, on=join_keys, how='inner')
    
    return joined_df

def time_based_split(df: pd.DataFrame):
    """
    Dynamic split: uses the two most recent complete seasons for val/test,
    everything earlier for training.
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    all_seasons = sorted(df['season'].unique())

    if len(all_seasons) < 3:
        # Fallback: use 80/10/10 by row count
        n = len(df)
        train = df.iloc[:int(n*0.8)].copy()
        val   = df.iloc[int(n*0.8):int(n*0.9)].copy()
        test  = df.iloc[int(n*0.9):].copy()
        return train, val, test

    test_season  = all_seasons[-1]   # most recent complete season
    val_season   = all_seasons[-2]   # second most recent
    # All others are training

    train_mask = df['season'] < val_season
    val_mask   = df['season'] == val_season
    test_mask  = df['season'] == test_season

    return df[train_mask].copy(), df[val_mask].copy(), df[test_mask].copy()

def drop_missing_targets(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """Drops rows where the target column is missing and logs the operation."""
    if df.empty:
        return df
        
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataframe.")
        
    initial_rows = len(df)
    valid_mask = ~df[target_col].isna()
    filtered_df = df[valid_mask].copy()
    dropped_rows = initial_rows - len(filtered_df)
    
    print(f"Target Drop [{target_col}]: Initial rows: {initial_rows} | Dropped: {dropped_rows} | Remaining: {len(filtered_df)}")
    
    if len(filtered_df) == 0:
        raise ValueError(f"Zero rows remaining after dropping missing values for target '{target_col}'.")
        
    return filtered_df
