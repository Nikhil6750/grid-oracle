"""
Fix all 5 model problems for better podium prediction.

Problem 1: Season form drowns out weekend form
  → Add weekend_momentum_score combining quali + sprint + teammate delta

Problem 2: Quali gap not weighted enough  
  → Add pole_gap_rank (rank by quali gap within round)

Problem 3: Sprint win not learned
  → Add sprint_podium_flag, sprint_winner_flag explicit binary features

Problem 4: No current weekend momentum
  → Add weekend_sweep_score (how dominant this weekend specifically)

Problem 5: Circuit history not explicit enough
  → Add circuit_podium_rate derived from avg_finish
"""

import pandas as pd
import numpy as np

PARQUET_PATH = "data/features/race_features.parquet"

df = pd.read_parquet(PARQUET_PATH)
print(f"Loaded {len(df)} rows")

# ── PROBLEM 3 FIX: Explicit sprint binary features ──────────────────────────
print("\n[Fix 3] Adding sprint binary features...")
df['sprint_winner_flag'] = (df['sprint_position'] == 1).astype(float)
df['sprint_podium_flag'] = (df['sprint_position'] <= 3).astype(float)
df['sprint_top8_flag'] = (df['sprint_position'] <= 8).astype(float)
df['sprint_winner_flag_missing'] = df['sprint_position_missing']
df['sprint_podium_flag_missing'] = df['sprint_position_missing']
df['sprint_top8_flag_missing'] = df['sprint_position_missing']

# ── PROBLEM 2 FIX: Quali gap rank within round ──────────────────────────────
print("[Fix 2] Adding quali gap rank feature...")
def add_quali_rank(group):
    group = group.copy()
    group['quali_gap_rank'] = group['quali_gap_to_pole_s'].rank(method='min')
    group['quali_gap_rank_missing'] = group['quali_gap_to_pole_s_missing']
    return group

df = df.groupby(['season', 'round', 'prediction_stage'], group_keys=False).apply(add_quali_rank)

# ── PROBLEM 4 FIX: Weekend momentum score ───────────────────────────────────
print("[Fix 4] Adding weekend momentum score...")
def add_weekend_momentum(group):
    group = group.copy()
    
    # Normalize quali gap (pole=1.0, worst=0.0)
    max_gap = group['quali_gap_to_pole_s'].max()
    if max_gap > 0:
        quali_score = 1 - (group['quali_gap_to_pole_s'] / max_gap)
    else:
        quali_score = pd.Series(0.5, index=group.index)
    
    # Sprint score (only on sprint weekends)
    is_sprint = group['sprint_weekend_flag'].max() == 1
    if is_sprint and group['sprint_position'].notna().any():
        max_pos = group['sprint_position'].max()
        sprint_score = 1 - ((group['sprint_position'] - 1) / max_pos)
    else:
        sprint_score = pd.Series(0.0, index=group.index)
    
    # Teammate delta score
    td = group['teammate_qualifying_delta']
    teammate_score = (td > 0).astype(float)  # 1 if faster than teammate
    
    # Weighted combination
    group['weekend_momentum_score'] = (
        quali_score * 0.45 +
        sprint_score * 0.35 +
        teammate_score * 0.20
    ).round(4)
    group['weekend_momentum_score_missing'] = 0
    return group

df = df.groupby(['season', 'round', 'prediction_stage'], group_keys=False).apply(add_weekend_momentum)

# ── PROBLEM 5 FIX: Circuit podium rate ──────────────────────────────────────
print("[Fix 5] Adding circuit podium rate...")
df['circuit_podium_rate'] = (
    df['driver_circuit_avg_finish_before_event'].apply(
        lambda x: max(0, 1 - (x - 1) / 9) if pd.notna(x) else 0
    )
).round(4)
df['circuit_podium_rate_missing'] = df['driver_circuit_avg_finish_before_event_missing']

# ── PROBLEM 1 FIX: Recent form weight — last 3 vs last 5 ratio ──────────────
print("[Fix 1] Adding form recency ratio...")
df['form_recency_ratio'] = (
    df['driver_last_3_finish_avg'] / 
    df['driver_last_5_finish_avg'].replace(0, np.nan)
).fillna(1.0).round(4)
# Lower = improving form (last 3 better than last 5)
df['form_recency_ratio_missing'] = (
    df['driver_last_3_finish_avg_missing'] | 
    df['driver_last_5_finish_avg_missing']
).astype(int)

# Save
df.to_parquet(PARQUET_PATH, index=False)
print(f"\nSaved {len(df)} rows with new features")

# Verify for R5
r5 = df[
    (df['season']==2026) & 
    (df['round']==5) & 
    (df['prediction_stage']=='post_qualifying')
][['driver_code', 'weekend_momentum_score', 'sprint_winner_flag', 
   'sprint_podium_flag', 'quali_gap_rank', 'circuit_podium_rate',
   'form_recency_ratio']].sort_values('weekend_momentum_score', ascending=False)

print("\n2026 R5 New Features:")
print(r5.to_string())