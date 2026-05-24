import pandas as pd
import numpy as np

def rank_drivers_by_prediction(df: pd.DataFrame, preds: np.ndarray, descending: bool = True) -> pd.DataFrame:
    """
    Ranks drivers within a race based on predicted scores or probabilities.
    descending=True for probabilities (higher is better).
    descending=False for positions (lower is better).
    """
    df_ranked = df[['season', 'round', 'driver_code']].copy()
    df_ranked['score'] = preds
    
    # Sort within each race
    df_ranked = df_ranked.sort_values(
        by=['season', 'round', 'score'], 
        ascending=[True, True, not descending]
    )
    
    # Assign rank
    df_ranked['predicted_rank'] = df_ranked.groupby(['season', 'round']).cumcount() + 1
    
    return df_ranked

def get_top_k_ranked_drivers(df_ranked: pd.DataFrame, k: int) -> pd.DataFrame:
    """Returns the top k drivers per race from the ranked DataFrame."""
    return df_ranked[df_ranked['predicted_rank'] <= k]
