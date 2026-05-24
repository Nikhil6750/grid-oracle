import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

# STEP 1 — Parse arguments
parser = argparse.ArgumentParser(description="Generate pre-weekend feature rows for an upcoming race.")
parser.add_argument("--season", type=int, required=True, help="Target season (e.g., 2026)")
parser.add_argument("--round", type=int, required=True, help="Target round (e.g., 5)")
parser.add_argument("--force", action="store_true", help="Overwrite existing rows if present")
args = parser.parse_args()

target_season = args.season
target_round = args.round
force = args.force

# STEP 2 — Resolve project root
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

# STEP 3 — Load event manifest for the target round
manifest_path = ROOT_DIR / f"data/processed/sessions/season={target_season}/round={target_round:02d}/event_manifest.json"
if not manifest_path.exists():
    print(f"No event_manifest.json found for season {target_season} round {target_round}.")
    print(f"Run ingestion first: python scripts/ingest_historical.py --season {target_season} --round {target_round} --sessions Q S R")
    sys.exit(1)

with open(manifest_path, "r") as f:
    manifest = json.load(f)

event_name = manifest.get("event_name", manifest.get("EventName", "Unknown Event"))
event_format = manifest.get("event_format", manifest.get("EventFormat", "conventional"))

# STEP 4 — Find the most recent completed race round
# Scan data/processed/sessions/season={season}/ for the highest round number that has an R_results.parquet file.
ref_season = target_season
ref_round = None

def get_highest_completed_round(season):
    season_dir = ROOT_DIR / f"data/processed/sessions/season={season}"
    if not season_dir.exists():
        return None
    
    highest_rnd = None
    for round_dir in season_dir.iterdir():
        if round_dir.is_dir() and round_dir.name.startswith("round="):
            try:
                rnd_num = int(round_dir.name.split("=")[1])
                r_results = round_dir / "R_results.parquet"
                if r_results.exists():
                    if highest_rnd is None or rnd_num > highest_rnd:
                        highest_rnd = rnd_num
            except ValueError:
                continue
    return highest_rnd

# First try target season
ref_round = get_highest_completed_round(target_season)

# If no completed race exists for the season, scan the previous season
if ref_round is None:
    ref_season = target_season - 1
    ref_round = get_highest_completed_round(ref_season)

if ref_round is None:
    print(f"Could not find any completed race in {target_season} or {target_season-1} to use as reference lineup.")
    sys.exit(1)

print(f"Using Season {ref_season} Round {ref_round} as reference for driver lineup.")

# STEP 5 — Check for existing rows
parquet_path = ROOT_DIR / "data/features/race_features.parquet"
if parquet_path.exists():
    existing = pd.read_parquet(parquet_path)
    mask = (existing['season'] == target_season) & \
           (existing['round'] == target_round) & \
           (existing['prediction_stage'] == 'pre_weekend')
    
    if mask.any() and not force:
        print(f"pre_weekend features already exist for {target_season} R{target_round}. Use --force to overwrite.")
        sys.exit(0)
else:
    existing = pd.DataFrame()

# STEP 6 — Load all ingested race data via DataLoader
from src.feature_engineering.data_loader import DataLoader
loader = DataLoader()
r_df_all = loader.load_session_results('R')
q_df_all = loader.load_session_results('Q')
s_df_all = loader.load_session_results('S')

# Filter to only seasons <= target_season and rounds < target_round for the target_season (to prevent leakage)
def filter_leakage(df):
    if df.empty:
        return df
    return df[
        (df['season'] < target_season) | 
        ((df['season'] == target_season) & (df['round'] < target_round))
    ]

r_df = filter_leakage(r_df_all)
q_df = filter_leakage(q_df_all)
s_df = filter_leakage(s_df_all)

# STEP 7 — Get driver lineup from the reference round
ref_round_results = r_df[
    (r_df['season'] == ref_season) & (r_df['round'] == ref_round)
]

if ref_round_results.empty:
    print(f"Reference round {ref_season} R{ref_round} not found in loaded data.")
    sys.exit(1)

# STEP 8 — Build the skeleton DataFrame for the target round
skeleton = ref_round_results[['driver_number', 'driver_code', 'team']].drop_duplicates().copy()
skeleton['season'] = target_season
skeleton['round'] = target_round
skeleton['event_name'] = event_name

# Determine sprint_weekend_flag
sprint_weekend_flag = 1 if event_format in ['sprint_qualifying', 'sprint'] else 0
skeleton['sprint_weekend_flag'] = sprint_weekend_flag

# Add stage features
skeleton['prediction_stage'] = 'pre_weekend'
skeleton['feature_cutoff_stage'] = 'pre_weekend'
skeleton['feature_source_sessions'] = 'historical_only'
skeleton['feature_cutoff_timestamp'] = datetime.utcnow().isoformat()

# STEP 9 — Build historical driver and team features
# We inject synthetic placeholder rows for the target round into r_df so that
# DriverFeatureBuilder's shift(1) rolling logic generates forward-looking
# features for round N from rounds 1..(N-1). Without this injection,
# round N never appears in r_df and the feature filter below returns empty.
import numpy as np
from src.feature_engineering.driver_features import DriverFeatureBuilder
from src.feature_engineering.team_features import TeamFeatureBuilder

synth_rows = skeleton[['driver_number', 'driver_code', 'team']].copy()
synth_rows['season'] = target_season
synth_rows['round'] = target_round
synth_rows['event_name'] = event_name
# Fill every other column in r_df with NaN so the builder sees a real row
# but the actual race results are absent (they haven't happened yet).
for col in r_df.columns:
    if col not in synth_rows.columns:
        synth_rows[col] = np.nan
synth_rows = synth_rows.reindex(columns=r_df.columns)

r_df_augmented = pd.concat([r_df, synth_rows], ignore_index=True)

db = DriverFeatureBuilder(r_df_augmented, q_df)
driver_feats_all = db.build_features()

tb = TeamFeatureBuilder(r_df_augmented, q_df)
team_feats_all = tb.build_features()

from src.feature_engineering.weather_features import WeatherFeatureBuilder
from src.feature_engineering.wet_skill_features import WetSkillFeatureBuilder
from src.feature_engineering.strategy_features import TeamStrategyFeatureBuilder
from src.feature_engineering.qualifying_lap_features import QualifyingLapFeatureBuilder

r_weather = loader.load_session_weather('R')
wb_weather = WeatherFeatureBuilder(r_weather, 'R')
weather_index = wb_weather.build_features()

wsb = WetSkillFeatureBuilder(r_df_augmented, weather_index)
wet_feats_all = wsb.build_features()

r_laps = loader.load_session_laps('R')
tsb = TeamStrategyFeatureBuilder(r_laps, r_df_augmented)
strategy_feats_all = tsb.build_features()

q_laps = loader.load_session_laps('Q')
qlb = QualifyingLapFeatureBuilder(q_laps, q_df)
quali_lap_feats_all = qlb.build_features()

if not weather_index.empty:
    driver_feats_all = driver_feats_all.merge(weather_index, on=['season', 'round'], how='left')
if not wet_feats_all.empty:
    driver_feats_all = driver_feats_all.merge(wet_feats_all, on=['season', 'round', 'driver_code'], how='left')
if not quali_lap_feats_all.empty:
    driver_feats_all = driver_feats_all.merge(quali_lap_feats_all, on=['season', 'round', 'driver_code'], how='left')
if not strategy_feats_all.empty:
    team_feats_all = team_feats_all.merge(strategy_feats_all, on=['season', 'round', 'team'], how='left')

# Filter to season==target_season, round==target_round
driver_feats = driver_feats_all[
    (driver_feats_all['season'] == target_season) &
    (driver_feats_all['round'] == target_round)
]

team_feats = team_feats_all[
    (team_feats_all['season'] == target_season) &
    (team_feats_all['round'] == target_round)
]

# STEP 10 — Merge features onto skeleton
df = skeleton.merge(driver_feats, on=['season', 'round', 'driver_code'], how='left')
df = df.merge(team_feats, on=['season', 'round', 'team'], how='left')

from src.feature_engineering.circuit_features import CircuitFeatureBuilder
circuit_meta = loader.load_circuit_metadata()
if not circuit_meta.empty:
    cb = CircuitFeatureBuilder(circuit_meta)
    df = cb.add_circuit_features(df)

# STEP 11 — Add cross-sectional features
# Championship rank
df['driver_championship_rank_before_event'] = (
    df.groupby(['season', 'round'])['driver_season_points_before_event']
    .rank(ascending=False, method='min')
).fillna(11)

df['team_constructor_rank_before_event'] = (
    df.groupby(['season', 'round'])['team_season_points_before_event']
    .rank(ascending=False, method='min')
).fillna(6)

# Regulation era
def _get_era(s):
    if s <= 2021: return 0
    elif s <= 2025: return 1
    else: return 2
df['season_regulation_era'] = df['season'].apply(_get_era)

# Impute new fields that might be NaN if missing history
df['driver_last_3_finish_avg'] = df.get('driver_last_3_finish_avg', pd.Series(dtype=float)).fillna(10.0)
df['driver_form_trend'] = df.get('driver_form_trend', pd.Series(dtype=float)).fillna(0.0)
df['driver_season_podium_rate_before_event'] = df.get('driver_season_podium_rate_before_event', pd.Series(dtype=float)).fillna(0.0)

# STEP 11B — Inject live news features (penalties, weather forecast)
try:
    from src.data_ingestion.news_scraper import scrape_f1_news
    from src.feature_engineering.news_features import NewsFeatureBuilder
    news = scrape_f1_news(event_name=event_name, season=target_season, round_num=target_round)
    driver_codes = df['driver_code'].dropna().unique().tolist()
    nb = NewsFeatureBuilder(news, driver_codes)
    news_feats = nb.build_features()
    if not news_feats.empty:
        df = df.merge(news_feats, on='driver_code', how='left')
    print(f"News features injected: penalties={news.get('grid_penalties', {})}, "
          f"wet_prob={news.get('wet_race_probability', 'N/A')}")
except Exception as e:
    print(f"[WARN] News feature injection failed (non-fatal): {e}")

# STEP 12 — Ensure qualifying and sprint missing columns
from src.feature_engineering.feature_store import FeatureStore
fs = FeatureStore()
df = fs._ensure_qualifying_columns(df)
df = fs._ensure_sprint_columns(df)
df = fs._fix_all_missing_indicators(df)

# Do NOT impute target variables because LeakageGuard forbids them

# STEP 13 — Append to race_features.parquet

# Safety: strip forbidden/target columns from the new rows BEFORE concat.
# These can sneak in if DriverFeatureBuilder or TeamFeatureBuilder surfaces raw
# result columns, or if existing parquet alignment adds them back via pd.concat.
# prediction_service.py also strips them at inference time (defense-in-depth).
_FORBIDDEN_INFERENCE_COLS = [
    'race_finish_position', 'finishing_position', 'classified_position',
    'classifiedposition', 'position', 'points', 'status', 'podium',
    'top10', 'winner', 'result', 'grid_position', 'race_result',
]
cols_to_strip = [
    c for c in df.columns
    if c in _FORBIDDEN_INFERENCE_COLS
    or c.lower().startswith('target_')
    or '_target' in c.lower()
]
if cols_to_strip:
    print(f"Stripping forbidden columns from new rows before parquet write: {cols_to_strip}")
    df = df.drop(columns=cols_to_strip)

if not existing.empty:
    if force:
        mask = (existing['season'] == target_season) & \
               (existing['round'] == target_round) & \
               (existing['prediction_stage'] == 'pre_weekend')
        existing = existing[~mask]

    combined = pd.concat([existing, df], ignore_index=True)
else:
    combined = df

# Final check: _fix_all_missing_indicators iterates through all columns with
# _missing suffix and sets them properly. Already called above on df, but
# re-run on combined in case concat alignment introduced new NaN indicators.

combined.to_parquet(parquet_path)

drivers_list = sorted(df['driver_code'].dropna().unique().tolist())
print(f"Added {len(df)} pre_weekend feature rows for {target_season} R{target_round} ({event_name}) to race_features.parquet")
print(f"Drivers: {drivers_list}")
