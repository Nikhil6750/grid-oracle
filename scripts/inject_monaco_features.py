"""
Add street circuit modifier and qualifying position weight boost
for Monaco and other street circuits.
"""
import pandas as pd
import numpy as np

PARQUET_PATH = "data/features/race_features.parquet"

# Street circuits where qualifying position dominates
STREET_CIRCUITS = [
    'monaco', 'baku', 'marina_bay', 'vegas', 
    'miami', 'villeneuve', 'jeddah', 'albert_park'
]

df = pd.read_parquet(PARQUET_PATH)
print(f"Loaded {len(df)} rows")

# Add street circuit flag
df['is_street_circuit'] = df['circuit_id'].isin(STREET_CIRCUITS).astype(float)
df['is_street_circuit_missing'] = 0

# Add qualifying dominance score
# On street circuits, qualifying position is 3x more predictive
def add_quali_dominance(group):
    group = group.copy()
    is_street = group['is_street_circuit'].max() == 1
    
    if 'quali_gap_to_pole_s' in group.columns:
        gap = group['quali_gap_to_pole_s'].fillna(3.0)
        max_gap = gap.max()
        if max_gap > 0:
            normalized = 1 - (gap / max_gap)
        else:
            normalized = pd.Series(0.5, index=group.index)
        
        # Triple weight for street circuits
        multiplier = 3.0 if is_street else 1.0
        group['quali_dominance_score'] = (normalized * multiplier).round(4)
    else:
        group['quali_dominance_score'] = 0.5
    
    group['quali_dominance_score_missing'] = 0
    return group

df = df.groupby(
    ['season', 'round', 'prediction_stage'], 
    group_keys=False
).apply(add_quali_dominance)

# Add street circuit qualifying rank
# Lower gap to pole on street circuit = much stronger signal
df['street_quali_advantage'] = (
    df['is_street_circuit'] * (1 - df['quali_gap_to_pole_s'].fillna(3.0) / 3.0)
).round(4)
df['street_quali_advantage_missing'] = 0

# Verify Monaco R6
r6 = df[
    (df['season']==2026) & 
    (df['round']==6) & 
    (df['prediction_stage']=='post_qualifying')
][['driver_code', 'is_street_circuit', 'quali_dominance_score', 
   'street_quali_advantage', 'quali_gap_to_pole_s']].sort_values(
    'quali_dominance_score', ascending=False
)

print("\n2026 R6 Monaco Street Circuit Features:")
print(r6.to_string())

df.to_parquet(PARQUET_PATH, index=False)
print(f"\nSaved to {PARQUET_PATH}")