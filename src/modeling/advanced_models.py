import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier

def get_qualifying_advanced_model():
    """HistGradientBoostingRegressor for qualifying position prediction."""
    return HistGradientBoostingRegressor(
        random_state=42,
        max_iter=300,
        learning_rate=0.1,
        max_depth=6,
        max_leaf_nodes=31,
        min_samples_leaf=10,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=15
    )

def get_race_finish_advanced_model():
    """HistGradientBoostingRegressor for race finish position prediction."""
    return HistGradientBoostingRegressor(
        random_state=42,
        max_iter=300,
        learning_rate=0.1,
        max_depth=6,
        max_leaf_nodes=31,
        min_samples_leaf=10,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=15
    )

def get_podium_advanced_model():
    """HistGradientBoostingClassifier for binary podium prediction."""
    return HistGradientBoostingClassifier(
        random_state=42,
        max_iter=300,
        learning_rate=0.1,
        max_depth=5,
        max_leaf_nodes=31,
        min_samples_leaf=10,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=15,
        class_weight='balanced'
    )

def get_top10_advanced_model():
    """HistGradientBoostingClassifier for binary top10 prediction."""
    return HistGradientBoostingClassifier(
        random_state=42,
        max_iter=300,
        learning_rate=0.1,
        max_depth=5,
        max_leaf_nodes=31,
        min_samples_leaf=10,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=15,
        class_weight='balanced'
    )
