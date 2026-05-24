"""
Quick fix: inject sprint results + weather flag for 2026 R5
before retraining for Canadian GP prediction.
"""
import pandas as pd
import numpy as np

PARQUET_PATH = "data/features/race_features.parquet"

# Canadian GP 2026 Sprint results
SPRINT_RESULTS = {
    'RUS': {'sprint_position': 1, 'sprint_points': 8, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 1},
    'ANT': {'sprint_position': 2, 'sprint_points': 7, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'NOR': {'sprint_position': 3, 'sprint_points': 6, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 1},
    'PIA': {'sprint_position': 4, 'sprint_points': 5, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'HAM': {'sprint_position': 5, 'sprint_points': 4, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'VER': {'sprint_position': 6, 'sprint_points': 3, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'LEC': {'sprint_position': 7, 'sprint_points': 2, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'HAD': {'sprint_position': 8, 'sprint_points': 1, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'COL': {'sprint_position': 9, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'LIN': {'sprint_position': 10, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'BEA': {'sprint_position': 11, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'HUL': {'sprint_position': 12, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'LAW': {'sprint_position': 13, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'GAS': {'sprint_position': 14, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'SAI': {'sprint_position': 15, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'BOR': {'sprint_position': 16, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'OCO': {'sprint_position': 17, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'ALO': {'sprint_position': 18, 'sprint_points': 0, 'sprint_finish_status': 'DNF', 'sprint_position_gain_loss': -2},
    'PER': {'sprint_position': 19, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'BOT': {'sprint_position': 20, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
    'ALB': {'sprint_position': 21, 'sprint_points': 0, 'sprint_finish_status': 'DNF', 'sprint_position_gain_loss': 0},
    'STR': {'sprint_position': 22, 'sprint_points': 0, 'sprint_finish_status': 'Finished', 'sprint_position_gain_loss': 0},
}

df = pd.read_parquet(PARQUET_PATH)
mask = (df['season']==2026) & (df['round']==5) & (df['prediction_stage']=='post_qualifying')

print(f"Updating {mask.sum()} rows for 2026 R5 post_qualifying...")

for driver, stats in SPRINT_RESULTS.items():
    driver_mask = mask & (df['driver_code'] == driver)
    if driver_mask.sum() == 0:
        print(f"  [WARN] {driver} not found in R5 features")
        continue
    for col, val in stats.items():
        df.loc[driver_mask, col] = val
        df.loc[driver_mask, f'{col}_missing'] = 0
    print(f"  {driver}: sprint P{stats['sprint_position']}")

# Fix weather rainfall flag — rain predicted for Canadian GP
df.loc[mask, 'weather_rainfall_flag'] = 1.0
df.loc[mask, 'weather_rainfall_flag_missing'] = 0
print("\nWeather rainfall flag set to 1.0 (rain predicted)")

df.to_parquet(PARQUET_PATH, index=False)
print(f"\nSaved to {PARQUET_PATH}")
print("Now run: python scripts/train_advanced.py --stage post_qualifying")
print("Then run: python scripts/predict_advanced.py --season 2026 --round 5 --stage post_qualifying")