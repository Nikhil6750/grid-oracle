import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier, VotingClassifier, VotingRegressor, RandomForestClassifier, RandomForestRegressor
from xgboost import XGBRegressor, XGBClassifier

def get_qualifying_advanced_model():
    hgb = HistGradientBoostingRegressor(
        random_state=42, max_iter=300, learning_rate=0.05,
        max_depth=5, max_leaf_nodes=31, min_samples_leaf=10,
        early_stopping=True, validation_fraction=0.1, n_iter_no_change=15
    )
    xgb = XGBRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=5,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
        verbosity=0, eval_metric='mae'
    )
    rf = RandomForestRegressor(
        n_estimators=200, max_depth=8, random_state=42, n_jobs=-1
    )
    return VotingRegressor(estimators=[
        ('hgb', hgb), ('xgb', xgb), ('rf', rf)
    ])

def get_race_finish_advanced_model():
    hgb = HistGradientBoostingRegressor(
        random_state=42, max_iter=400, learning_rate=0.05,
        max_depth=6, max_leaf_nodes=31, min_samples_leaf=8,
        early_stopping=True, validation_fraction=0.1, n_iter_no_change=20
    )
    xgb = XGBRegressor(
        n_estimators=400, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
        verbosity=0, eval_metric='mae'
    )
    rf = RandomForestRegressor(
        n_estimators=300, max_depth=10, random_state=42, n_jobs=-1
    )
    return VotingRegressor(estimators=[
        ('hgb', hgb), ('xgb', xgb), ('rf', rf)
    ])

def get_podium_advanced_model():
    hgb = HistGradientBoostingClassifier(
        random_state=42, max_iter=400, learning_rate=0.05,
        max_depth=5, max_leaf_nodes=31, min_samples_leaf=8,
        early_stopping=True, validation_fraction=0.1, n_iter_no_change=20,
        class_weight='balanced'
    )
    xgb = XGBClassifier(
        n_estimators=400, learning_rate=0.05, max_depth=5,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
        verbosity=0, eval_metric='logloss', scale_pos_weight=6
    )
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=8, class_weight='balanced',
        random_state=42, n_jobs=-1
    )
    return VotingClassifier(estimators=[
        ('hgb', hgb), ('xgb', xgb), ('rf', rf)
    ], voting='soft')

def get_top10_advanced_model():
    hgb = HistGradientBoostingClassifier(
        random_state=42, max_iter=300, learning_rate=0.05,
        max_depth=4, max_leaf_nodes=31, min_samples_leaf=10,
        early_stopping=True, validation_fraction=0.1, n_iter_no_change=15,
        class_weight='balanced'
    )
    xgb = XGBClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=4,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
        verbosity=0, eval_metric='logloss', scale_pos_weight=1
    )
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=6, class_weight='balanced',
        random_state=42, n_jobs=-1
    )
    return VotingClassifier(estimators=[
        ('hgb', hgb), ('xgb', xgb), ('rf', rf)
    ], voting='soft')

def get_wet_race_podium_model():
    """Separate model trained only on wet race data."""
    xgb = XGBClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=4,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
        verbosity=0, eval_metric='logloss', scale_pos_weight=6
    )
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=6, class_weight='balanced',
        random_state=42, n_jobs=-1
    )
    return VotingClassifier(estimators=[
        ('xgb', xgb), ('rf', rf)
    ], voting='soft')
