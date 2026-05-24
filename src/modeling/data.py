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
    """Splits data into train (2018-2022), val (2023), and test (2024)."""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    train_mask = (df['season'] >= 2018) & (df['season'] <= 2022)
    val_mask = (df['season'] == 2023)
    test_mask = (df['season'] == 2024)
    
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
