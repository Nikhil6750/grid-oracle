import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

def get_qualifying_model():
    """Returns baseline model for qualifying prediction."""
    return RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)

def get_race_finish_model():
    """Returns baseline model for race finish prediction."""
    return RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)

def get_podium_model():
    """Returns baseline classifier for podium prediction."""
    return LogisticRegression(random_state=42, max_iter=1000, class_weight='balanced')

def get_top10_model():
    """Returns baseline classifier for top 10 prediction."""
    return LogisticRegression(random_state=42, max_iter=1000, class_weight='balanced')

def naive_qualifying_prediction(df: pd.DataFrame):
    """Predicts driver_last_5_qualifying_avg."""
    if 'driver_last_5_qualifying_avg' in df.columns:
        return df['driver_last_5_qualifying_avg'].fillna(20.0)
    return pd.Series(20.0, index=df.index)

def naive_race_finish_pre_weekend(df: pd.DataFrame):
    """Predicts driver_last_5_finish_avg."""
    if 'driver_last_5_finish_avg' in df.columns:
        return df['driver_last_5_finish_avg'].fillna(20.0)
    return pd.Series(20.0, index=df.index)

def naive_race_finish_post_qualifying(df: pd.DataFrame):
    """Predicts qualifying_position."""
    if 'qualifying_position' in df.columns:
        return df['qualifying_position'].fillna(20.0)
    return pd.Series(20.0, index=df.index)

def naive_podium_pre_weekend(df: pd.DataFrame):
    """Top 3 by driver_last_5_finish_avg."""
    preds = naive_race_finish_pre_weekend(df)
    return -preds, (preds <= 3).astype(int)

def naive_podium_post_qualifying(df: pd.DataFrame):
    """Top 3 by qualifying_position."""
    preds = naive_race_finish_post_qualifying(df)
    return -preds, (preds <= 3).astype(int)

def naive_top10_pre_weekend(df: pd.DataFrame):
    """Top 10 by driver_last_5_finish_avg."""
    preds = naive_race_finish_pre_weekend(df)
    return -preds, (preds <= 10).astype(int)

def naive_top10_post_qualifying(df: pd.DataFrame):
    """Top 10 by qualifying_position."""
    preds = naive_race_finish_post_qualifying(df)
    return -preds, (preds <= 10).astype(int)
