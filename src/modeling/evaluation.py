import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, roc_auc_score, average_precision_score, precision_score, recall_score

def evaluate_regression(y_true: np.ndarray, y_pred: np.ndarray, df: pd.DataFrame, task_name: str) -> dict:
    """Evaluates regressors: MAE, RMSE, and Top 1 accuracy by race."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = root_mean_squared_error(y_true, y_pred)
    
    # Calculate ranking accuracy
    df_eval = df[['season', 'round', 'driver_code']].copy()
    df_eval['y_true'] = y_true
    df_eval['y_pred'] = y_pred
    
    correct_top1 = 0
    total_races = 0
    
    for (season, rnd), group in df_eval.groupby(['season', 'round']):
        # Ignore races where no one has a valid target (e.g., all nan or empty)
        if group['y_true'].isna().all():
            continue
            
        actual_winner = group.loc[group['y_true'].idxmin()]['driver_code']
        predicted_winner = group.loc[group['y_pred'].idxmin()]['driver_code']
        
        if actual_winner == predicted_winner:
            correct_top1 += 1
        total_races += 1
        
    top1_acc = correct_top1 / total_races if total_races > 0 else 0.0
    
    metrics = {
        'mae': float(mae),
        'rmse': float(rmse),
        f'{task_name}_top1_accuracy': float(top1_acc)
    }
    return metrics

def evaluate_classification(y_true: np.ndarray, y_pred_proba: np.ndarray, y_pred: np.ndarray, df: pd.DataFrame, k: int) -> dict:
    """Evaluates classifiers: ROC AUC, PR AUC, precision, recall, Top K accuracy by race."""
    roc_auc = roc_auc_score(y_true, y_pred_proba) if len(np.unique(y_true)) > 1 else np.nan
    pr_auc = average_precision_score(y_true, y_pred_proba) if len(np.unique(y_true)) > 1 else np.nan
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    
    # Top K accuracy by race
    df_eval = df[['season', 'round', 'driver_code']].copy()
    df_eval['y_true'] = y_true
    df_eval['y_pred_proba'] = y_pred_proba
    
    correct_topk = 0
    total_races = 0
    
    for (season, rnd), group in df_eval.groupby(['season', 'round']):
        if group['y_true'].sum() == 0:
            continue # No positive cases
            
        actual_topk = set(group[group['y_true'] == 1]['driver_code'].values)
        
        # Predicted top k: sort by proba descending
        pred_topk = set(group.sort_values('y_pred_proba', ascending=False).head(len(actual_topk))['driver_code'].values)
        
        # Accuracy: intersection / actual length
        if len(actual_topk) > 0:
            correct_topk += len(actual_topk.intersection(pred_topk)) / len(actual_topk)
            total_races += 1
            
    topk_acc = correct_topk / total_races if total_races > 0 else 0.0
    
    metrics = {
        'roc_auc': float(roc_auc) if not np.isnan(roc_auc) else 0.0,
        'pr_auc': float(pr_auc) if not np.isnan(pr_auc) else 0.0,
        'precision': float(precision),
        'recall': float(recall),
        f'top{k}_accuracy': float(topk_acc)
    }
    return metrics
