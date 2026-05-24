# PitWall AI — Live Pre-Race Prediction Engine: Implementation Prompt

## Context & Goal

PitWall AI is a FastAPI + sklearn F1 prediction backend. The existing pipeline ingests
historical data via FastF1, builds rolling driver/team/circuit features, trains
HistGradientBoosting models, and returns predictions per stage (pre_weekend,
post_qualifying, post_sprint). It currently works end-to-end for 2026 races.

**The objective of this upgrade is to build a fully automated, live pre-race prediction
engine that:**
1. Auto-fetches and ingests the latest FastF1 session data after each session ends
   (Qualifying, Sprint Qualifying, Sprint Race)
2. Adds 4 new feature families: qualifying-session lap detail, weather, driver wet-skill,
   and team strategy DNA
3. Heavily weights 2026 in-season form so recent results dominate predictions
4. Scrapes live F1 news for grid penalties, engine changes, and weather alerts and
   injects them as binary override features
5. Outputs a confident **P1 / P2 / P3 podium ranking** (not just binary podium
   probability) with calibrated confidence scores via a dedicated Podium Ranker model
6. Exposes two new API endpoints and a CLI script for easy triggering

---

## Repository Map (key files to understand before touching anything)

```
pitwall-ai-backend/
├── src/
│   ├── api/
│   │   ├── main.py                         ← FastAPI app, routes
│   │   ├── prediction_service.py           ← run_prediction() — ALREADY FIXED, do not break
│   │   └── schemas.py                      ← Pydantic response models
│   ├── data_ingestion/
│   │   ├── base_ingestor.py
│   │   └── historical_ingestor.py          ← FastF1 wrapper; saves laps/results/weather parquets
│   ├── feature_engineering/
│   │   ├── data_loader.py                  ← loads parquets from data/processed/sessions/
│   │   ├── driver_features.py              ← rolling driver stats, shift(1) leakage-safe
│   │   ├── team_features.py
│   │   ├── circuit_features.py
│   │   ├── weekend_features.py             ← assembles per-stage feature rows
│   │   ├── feature_store.py                ← orchestrator; writes data/features/*.parquet
│   │   └── target_builder.py
│   └── modeling/
│       ├── preprocessing.py                ← LeakageGuard, FeatureSelector, StageFeatureDropper
│       ├── advanced_models.py
│       ├── data.py                         ← time_based_split
│       ├── ranking.py                      ← rank_drivers_by_prediction()
│       └── model_registry.py
├── scripts/
│   ├── ingest_historical.py
│   ├── build_features.py
│   ├── train_advanced.py
│   ├── generate_upcoming_race_features.py  ← ALREADY EXISTS; generates pre_weekend rows
│   └── predict_advanced.py
└── data/
    ├── processed/sessions/season=YYYY/round=RR/
    │   ├── event_manifest.json             ← {"event_name":..., "event_format":...}
    │   ├── R_laps.parquet / R_results.parquet / R_weather.parquet
    │   ├── Q_laps.parquet / Q_results.parquet / Q_weather.parquet
    │   └── S_laps.parquet / S_results.parquet / S_weather.parquet
    └── features/
        ├── race_features.parquet           ← primary feature store
        ├── qualifying_features.parquet
        └── sprint_features.parquet
```

---

## Critical constraints (do NOT violate these)

- **LeakageGuard** in `src/modeling/preprocessing.py` rejects any DataFrame that
  contains columns: `race_finish_position`, `position`, `points`, `grid_position`,
  `finishing_position`, or any `target_*` column. Never let these reach `model.predict()`.
  `prediction_service.py` already calls `_strip_forbidden()` before every `.predict()` call.
- **shift(1) discipline**: All rolling feature builders use `shift(1)` so that round-N
  features only use data from rounds 1..N-1. Maintain this invariant in all new builders.
- **Missing-indicator pattern**: Every new numeric feature `foo` must be accompanied by
  `foo_missing` (int 0/1). `FeatureStore._fix_all_missing_indicators()` does a final
  sweep but new builders must generate them too.
- **Parquet column alignment**: When `pd.concat([existing, new_rows])`, pandas NaN-fills
  columns present in one but not the other. The `_strip_forbidden()` in prediction_service
  handles this at inference. Do not double-strip in the feature builders.
- **generate_upcoming_race_features.py already works** — do not change STEP 9 (synthetic
  row injection) or STEP 13 (forbidden column strip before concat). Extend the script for
  new features but preserve its structure.

---

## Work Plan — 6 Phases

---

### PHASE 1 — New Feature Builders

#### 1A. `src/feature_engineering/qualifying_lap_features.py` (NEW FILE)

Build a `QualifyingLapFeatureBuilder` class that reads the `Q_laps.parquet` file for a
given round and produces per-driver features:

```python
class QualifyingLapFeatureBuilder:
    def __init__(self, q_laps_df: pd.DataFrame):
        ...
    def build_features(self) -> pd.DataFrame:
        # Returns one row per (season, round, driver_code) with:
        # - quali_best_lap_time_s       : personal best lap time in seconds
        # - quali_gap_to_pole_s         : gap to the fastest lap in the session (seconds)
        # - quali_gap_to_pole_pct       : gap as % of pole lap time
        # - quali_best_sector1_s        : fastest S1 across all Q laps
        # - quali_best_sector2_s        : fastest S2
        # - quali_best_sector3_s        : fastest S3
        # - quali_session_reached       : 1=Q1 exit, 2=Q2 exit, 3=Q3 participant
        # - quali_laps_completed        : total clean laps in session
        # - quali_consistency_score     : std dev of clean lap times (lower = more consistent)
        # Plus _missing indicators for every column above
```

Rules:
- "Clean lap" = lap where `IsPersonalBest` or `LapTime` is not NaN and lap is not deleted
- `quali_gap_to_pole_s` = driver's best time minus session minimum time (both in seconds)
- `quali_session_reached`: derive from result position — Q3 participant = 3, Q2 exit = 2, Q1 exit = 1
- Sector times columns in the parquet are already in seconds (timedelta converted during ingest)
- All NaN values get the _missing=1 treatment and are imputed with medians

#### 1B. `src/feature_engineering/weather_features.py` (NEW FILE)

Build a `WeatherFeatureBuilder` that reads `*_weather.parquet` files and produces
session-level weather summaries:

```python
class WeatherFeatureBuilder:
    def __init__(self, weather_df: pd.DataFrame, session_type: str):
        # session_type: 'Q', 'R', 'S'
        ...
    def build_features(self) -> dict:
        # Returns a dict (one row, broadcast to all drivers) with:
        # - weather_air_temp_avg         : mean AirTemp during session
        # - weather_track_temp_avg       : mean TrackTemp
        # - weather_humidity_avg         : mean Humidity
        # - weather_wind_speed_avg       : mean WindSpeed
        # - weather_rainfall_flag        : 1 if any Rainfall==True row exists, else 0
        # - weather_max_rainfall_minutes : count of rows where Rainfall==True
        # - weather_track_temp_delta     : max TrackTemp minus min TrackTemp (thermal swing)
        # Plus _missing for every column
```

Notes:
- FastF1 `session.weather_data` has columns: `Time`, `AirTemp`, `TrackTemp`, `Humidity`,
  `WindSpeed`, `WindDirection`, `Rainfall` (boolean)
- For qualifying: use only laps during Q3 time window if available, else entire session
- `weather_rainfall_flag` is the single most important feature — wet races are chaos

#### 1C. `src/feature_engineering/wet_skill_features.py` (NEW FILE)

Build a `WetSkillFeatureBuilder` that computes a driver's historical wet-weather
performance rating:

```python
class WetSkillFeatureBuilder:
    def __init__(self, r_results_df: pd.DataFrame, r_weather_index: pd.DataFrame):
        # r_weather_index: DataFrame with columns [season, round, weather_rainfall_flag]
        # built by aggregating WeatherFeatureBuilder outputs across all rounds
        ...
    def build_features(self) -> pd.DataFrame:
        # Returns one row per (season, round, driver_code) with:
        # - driver_wet_race_count        : number of wet races before this round (shift(1))
        # - driver_wet_avg_finish        : avg finish position in wet races (shift(1) rolling)
        # - driver_wet_podium_rate       : podium rate in wet races (shift(1))
        # - driver_wet_vs_dry_delta      : wet_avg_finish minus dry_avg_finish (negative = better in wet)
        # - driver_wet_skill_score       : composite: if wet_race_count < 3, use career avg; else rolling last 5 wet
        # Plus _missing indicators
```

Rules:
- A race is "wet" if `weather_rainfall_flag == 1` for that round's R session
- All calculations use `shift(1)` to prevent leakage
- For drivers with < 3 wet races, `driver_wet_skill_score` uses their overall avg finish
  as a neutral prior and `driver_wet_race_count_missing=1`
- `driver_wet_vs_dry_delta` = (wet avg finish) - (dry avg finish); negative means the
  driver is BETTER in wet than dry

#### 1D. `src/feature_engineering/strategy_features.py` (NEW FILE)

Build a `TeamStrategyFeatureBuilder` that computes per-team strategy DNA from lap data:

```python
class TeamStrategyFeatureBuilder:
    def __init__(self, r_laps_df: pd.DataFrame, r_results_df: pd.DataFrame):
        ...
    def build_features(self) -> pd.DataFrame:
        # Returns one row per (season, round, team) with:
        # - team_avg_pit_stops           : avg number of pit stops per car
        # - team_pit_stop_consistency    : std dev of pit lap numbers (earlier = more aggressive)
        # - team_undercut_attempts       : count of times team pitted before the car ahead
        # - team_overcut_attempts        : count of times team stayed out when car ahead pitted
        # - team_avg_stint_length        : average laps per stint across all cars
        # - team_tyre_hardness_preference: share of laps on Hard compound (0=soft-lover, 1=hard-lover)
        # Plus _missing indicators
```

Rules:
- `r_laps_df` has `PitInTime` / `PitOutTime` columns; a pit stop row has non-null `PitInTime`
- All features use only rounds BEFORE the target round (shift via group-level sort)
- For teams with < 5 races of data, fill with grid median
- `team_undercut_attempts`: for each stint, check if the car pitted while the car directly
  ahead in the results had a longer stint; count how often the team does this

---

### PHASE 2 — 2026 In-Season Form Features

Modify **`src/feature_engineering/driver_features.py`** — add the following inside
`build_features()`, in the per-driver loop, after existing features:

```python
# 2026 in-season form (only current season races count)
current_season_mask = driver_df['season'] == driver_df['season'].iloc[-1]
season_races = driver_df[current_season_mask].copy()

# Rolling last-3 finish average for current season only
season_last3_finish = season_races['Position'].shift(1).rolling(3, min_periods=1).mean()

# Points scored in last 3 races of this season
season_last3_points = season_races['Points'].shift(1).rolling(3, min_periods=1).sum()

# Momentum: improvement trend in current season (negative = getting better)
season_momentum = season_races['Position'].shift(1).diff().rolling(3, min_periods=2).mean()
```

Add these to the `feature_df` output alongside existing features, with _missing indicators.

Also add to `DriverFeatureBuilder`:
```python
# Qualifying pace consistency within current season (Q position rolling std dev)
if not self.quali.empty:
    season_quali = driver_df.merge(q_seasons, ...)
    season_quali_std = season_quali['quali_position'].shift(1).rolling(4, min_periods=2).std()
```

---

### PHASE 3 — Podium Position Ranker Model (P1 / P2 / P3)

Instead of only a binary podium classifier, add a **multi-class podium position model**
that predicts exactly P1, P2, or P3.

#### 3A. Add target column in `src/feature_engineering/target_builder.py`

In the `build()` method, after the existing target columns, add:
```python
# Podium position target: 1, 2, or 3 for podium finishers; NaN for non-podium
df['target_podium_position'] = df['race_finish_position'].where(
    df['race_finish_position'] <= 3, other=np.nan
)
```

#### 3B. Add `train_podium_ranker()` in `scripts/train_advanced.py`

```python
def train_podium_ranker(train, val, test, stage):
    """
    Trains a 3-class classifier (P1=1, P2=2, P3=3) on podium finishers only
    using RandomForestClassifier with class_weight='balanced'.
    Only rows where target_podium_position is not NaN are used.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.multiclass import OneVsRestClassifier

    # Filter to podium rows only
    podium_train = train[train['target_podium_position'].notna()].copy()
    podium_val   = val[val['target_podium_position'].notna()].copy()
    podium_test  = test[test['target_podium_position'].notna()].copy()

    if len(podium_train) < 30:
        print(f"[{stage}] Not enough podium rows to train ranker ({len(podium_train)}), skipping.")
        return

    y_train = podium_train['target_podium_position'].astype(int)
    y_val   = podium_val['target_podium_position'].astype(int)

    sample_weights = compute_sample_weights(podium_train)

    model = RandomForestClassifier(
        n_estimators=300, max_depth=6, class_weight='balanced',
        random_state=42, n_jobs=-1
    )
    pipeline = get_baseline_pipeline(model, stage)
    pipeline.fit(podium_train, y_train, model__sample_weight=sample_weights)

    registry.save_model(pipeline, f"podium_ranker_advanced_{stage}")
    print(f"[{stage}] Podium ranker trained and saved.")
```

Call `train_podium_ranker()` for all three stages at the end of the main block.

#### 3C. Update `src/api/prediction_service.py`

After the existing `# ---- Podium ----` block, add a **Podium Ranker** block:

```python
# ---- Podium Position Ranker (P1/P2/P3) ----
podium_position_prediction: dict = {}  # {"P1": "VER", "P2": "NOR", "P3": "PIA"}

# Get top-5 podium candidates from the existing podium model
if podium_ranking:
    top5_codes = [e["driver"] for e in podium_ranking[:5]]
    top5_df = r_df[r_df["driver_code"].isin(top5_codes)].copy()

    ranker, rnk_label, rnk_fb = _load_model_with_fallback(
        adv_registry, base_registry,
        f"podium_ranker_advanced_{stage}", f"podium_ranker_baseline_{stage}",
    )
    if ranker is not None and not top5_df.empty:
        models_used["podium_ranker"] = rnk_label
        pos_preds = ranker.predict(top5_df)   # array of [1,2,3,1,2] etc.
        pos_proba = ranker.predict_proba(top5_df)  # shape (n, 3), classes=[1,2,3]
        for idx, (_, row) in enumerate(top5_df.iterrows()):
            for class_idx, pos in enumerate(ranker.classes_):
                predictions.append({
                    "season": row["season"], "round": row["round"],
                    "event_name": row["event_name"], "driver_code": row["driver_code"],
                    "prediction_stage": stage, "task": f"podium_position_P{pos}",
                    "prediction": float(pos_preds[idx]),
                    "probability": float(pos_proba[idx][class_idx]),
                })
        # Build position map: highest P(class=k) driver wins position k
        position_map = {}
        for pos in [1, 2, 3]:
            class_idx = list(ranker.classes_).index(pos)
            probs_for_pos = {
                top5_df.iloc[i]["driver_code"]: pos_proba[i][class_idx]
                for i in range(len(top5_df))
            }
            position_map[f"P{pos}"] = max(probs_for_pos, key=probs_for_pos.get)
        podium_position_prediction = position_map
```

#### 3D. Update `src/api/schemas.py`

Add `podium_position_prediction: dict[str, str] = {}` to `PredictionResponse`.
e.g. `{"P1": "NOR", "P2": "VER", "P3": "PIA"}`

---

### PHASE 4 — Live News Injector (Grid Penalty & Weather Alert Features)

#### 4A. `src/data_ingestion/news_scraper.py` (NEW FILE)

```python
"""
Scrapes F1 news from motorsport.com and the-race.com for the upcoming round.
Returns structured penalty/alert dicts. Uses requests + BeautifulSoup.
Falls back to empty dict on any error so the pipeline never breaks.
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import dict

PENALTY_KEYWORDS = [
    'grid penalty', 'grid drop', 'pit lane start', 'disqualified',
    'engine change', 'gearbox change', 'reprimand', 'excluded'
]

WEATHER_KEYWORDS = ['rain', 'wet', 'shower', 'storm', 'thunderstorm', 'overcast']

def scrape_f1_news(event_name: str, season: int) -> dict:
    """
    Returns:
    {
        "grid_penalties": {"VER": 5, "HAM": 10},   # driver_code: positions dropped
        "wet_race_probability": 0.6,                 # 0-1 float from weather reports
        "safety_car_probability": 0.4,               # estimated from circuit + weather
        "news_items": ["VER: 5 place grid penalty for engine change", ...]
    }
    Falls back to empty dict on failure.
    """
    ...
```

Rules:
- Use `requests.get()` with a 5-second timeout and `headers={"User-Agent": "Mozilla/5.0"}`
- Parse page text with BeautifulSoup
- For grid penalties: look for patterns like "([A-Z]{3}).*?(\d+).*?grid pen" with regex
- For wet probability: count weather keyword occurrences in recent articles,
  normalise to 0-1
- NEVER raise exceptions — wrap everything in try/except and return `{}` on failure
- Cache results to `data/news_cache/round_{round}.json` so it's not re-fetched on every run

#### 4B. `src/feature_engineering/news_features.py` (NEW FILE)

```python
class NewsFeatureBuilder:
    def __init__(self, news_dict: dict, driver_codes: list[str]):
        ...
    def build_features(self) -> pd.DataFrame:
        # Returns one row per driver_code with:
        # - news_grid_penalty_positions   : 0 if no penalty, else N positions dropped
        # - news_grid_penalty_flag        : 1 if any penalty, else 0
        # - news_wet_race_probability     : float 0-1 from scraper
        # - news_safety_car_probability   : float 0-1
        # - news_data_available           : 1 if news was successfully fetched, else 0
        # Plus _missing indicators for all columns
```

#### 4C. Hook news features into `scripts/generate_upcoming_race_features.py`

After STEP 11 (cross-sectional features), add STEP 11B:

```python
# STEP 11B — Inject live news features (penalties, weather forecast)
try:
    from src.data_ingestion.news_scraper import scrape_f1_news
    from src.feature_engineering.news_features import NewsFeatureBuilder
    news = scrape_f1_news(event_name=event_name, season=target_season)
    driver_codes = df['driver_code'].dropna().unique().tolist()
    nb = NewsFeatureBuilder(news, driver_codes)
    news_feats = nb.build_features()
    df = df.merge(news_feats, on='driver_code', how='left')
    print(f"News features injected: penalties={news.get('grid_penalties', {})}, "
          f"wet_prob={news.get('wet_race_probability', 'N/A')}")
except Exception as e:
    print(f"[WARN] News feature injection failed (non-fatal): {e}")
```

---

### PHASE 5 — Automated Session Ingestion Pipeline

#### 5A. `scripts/ingest_latest_session.py` (NEW FILE)

```python
"""
Auto-ingests the most recent completed session for a given race round.
Detects which sessions are available (Q, SQ, S, R) and ingests only new ones.
Designed to be run after each session ends — e.g. via task scheduler or cron.

Usage:
    python scripts/ingest_latest_session.py --season 2026 --round 5
    python scripts/ingest_latest_session.py --season 2026 --round 5 --session Q
    python scripts/ingest_latest_session.py --auto   # scans for the current active round
"""
import argparse
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
import os; os.chdir(ROOT_DIR)

import fastf1
from src.data_ingestion.historical_ingestor import HistoricalIngestor
from src.utils.paths import PROCESSED_DATA_DIR

SESSION_SEQUENCE = ['SQ', 'S', 'Q', 'R']  # Sprint Qualifying, Sprint, Qualifying, Race

def ingest_session(season: int, round_num: int, session_type: str, force: bool = False):
    ingestor = HistoricalIngestor(force_overwrite=force)
    # ... call ingestor logic for one session type
    # Save laps, results, weather parquets to
    # data/processed/sessions/season={season}/round={round:02d}/
    ...

def find_current_active_round(season: int) -> int:
    # Use fastf1.get_event_schedule(season) to find the round where
    # EventDate is closest to today but not yet raced
    ...

if __name__ == '__main__':
    # after successful ingest, auto-trigger feature rebuild for that stage:
    # python scripts/build_features.py --season S --round R --stage post_qualifying
    ...
```

#### 5B. `scripts/pre_race_pipeline.py` (NEW FILE) — THE MASTER ORCHESTRATOR

```python
"""
Full automated pre-race pipeline. Run this before every Grand Prix.
It detects what data is available, ingests missing sessions, rebuilds features,
and outputs a final podium prediction.

Usage:
    python scripts/pre_race_pipeline.py --season 2026 --round 5
    python scripts/pre_race_pipeline.py --auto    # finds upcoming round automatically

Steps executed:
    1. Check which sessions are ingested for this round
    2. Ingest any available but not-yet-ingested sessions (Q, SQ, S)
    3. Rebuild post_qualifying or post_sprint features as appropriate
    4. Inject live news features (penalties, weather)
    5. Retrain or fine-tune the model on 2026 data if new rounds are available
    6. Run prediction and print the P1/P2/P3 podium result
    7. Save full prediction to reports/pre_race_prediction_YYYY_RXX.json
"""
import argparse, json, subprocess, sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
import os; os.chdir(ROOT_DIR)

def run_step(cmd: list, step_name: str):
    print(f"\n{'='*60}")
    print(f"STEP: {step_name}")
    print(f"CMD : {' '.join(cmd)}")
    print('='*60)
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"[WARN] {step_name} exited with code {result.returncode}")
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', type=int, default=2026)
    parser.add_argument('--round', type=int, required=False)
    parser.add_argument('--auto', action='store_true')
    parser.add_argument('--retrain', action='store_true',
                        help='Retrain models after ingesting new session data')
    args = parser.parse_args()

    season = args.season
    # If --auto, detect the upcoming round from fastf1 schedule
    if args.auto or not args.round:
        from scripts.ingest_latest_session import find_current_active_round
        round_num = find_current_active_round(season)
        print(f"Auto-detected upcoming round: {season} R{round_num}")
    else:
        round_num = args.round

    # Detect best available stage
    session_dir = ROOT_DIR / f"data/processed/sessions/season={season}/round={round_num:02d}"
    has_sprint   = (session_dir / "S_results.parquet").exists()
    has_quali    = (session_dir / "Q_results.parquet").exists()
    stage = 'post_sprint' if has_sprint else ('post_qualifying' if has_quali else 'pre_weekend')
    print(f"Prediction stage: {stage}")

    # Step 1: Ingest any new sessions
    run_step(['python', 'scripts/ingest_latest_session.py',
              '--season', str(season), '--round', str(round_num)],
             "Ingest latest session data")

    # Step 2: Generate/update features for the target round
    if stage == 'pre_weekend':
        run_step(['python', 'scripts/generate_upcoming_race_features.py',
                  '--season', str(season), '--round', str(round_num), '--force'],
                 "Generate pre_weekend features")
    else:
        run_step(['python', 'scripts/build_features.py',
                  '--season', str(season), '--stage', stage],
                 f"Build {stage} features")

    # Step 3: Optional retrain
    if args.retrain:
        run_step(['python', 'scripts/train_advanced.py', '--stage', stage],
                 f"Retrain models for {stage}")

    # Step 4: Predict and save
    from src.api.prediction_service import run_prediction
    result = run_prediction(season=season, round_num=round_num, stage=stage, save_parquet=True)

    out_path = ROOT_DIR / f"reports/pre_race_prediction_{season}_R{round_num:02d}_{stage}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"PITWALL AI — {season} Round {round_num} ({stage.upper()})")
    print(f"{'='*60}")
    pos_pred = result.get('podium_position_prediction', {})
    if pos_pred:
        print(f"  P1 (WINNER) : {pos_pred.get('P1', 'TBD')}")
        print(f"  P2          : {pos_pred.get('P2', 'TBD')}")
        print(f"  P3          : {pos_pred.get('P3', 'TBD')}")
    else:
        print(f"  Race Winner : {result.get('race_winner_candidate', 'TBD')}")
        for i, e in enumerate(result.get('podium_ranking', [])[:3], 1):
            print(f"  P{i}          : {e['driver']} ({e['probability']*100:.1f}%)")
    print(f"\nFull prediction saved to: {out_path.name}")
    print(f"Warnings: {result.get('warnings', [])}")

if __name__ == '__main__':
    main()
```

---

### PHASE 6 — API Endpoints

#### 6A. Add to `src/api/main.py`

```python
@app.post("/ingest/session")
async def ingest_session_endpoint(season: int, round: int, session: str = "Q"):
    """
    Triggers FastF1 ingestion for a specific session.
    session: Q, S, SQ, R
    Returns: {"status": "ingested", "rows": N}
    """
    import subprocess
    result = subprocess.run(
        ['python', 'scripts/ingest_latest_session.py',
         '--season', str(season), '--round', str(round), '--session', session],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT)
    )
    return {"status": "ok" if result.returncode == 0 else "error",
            "stdout": result.stdout[-2000:], "stderr": result.stderr[-500:]}


@app.get("/predict/podium")
async def predict_podium(season: int = 2026, round: int = Query(...), stage: str = "post_qualifying"):
    """
    Returns P1/P2/P3 podium position predictions.
    Simpler endpoint focused on the podium ranker output.
    """
    from src.api.prediction_service import run_prediction
    try:
        result = run_prediction(season=season, round_num=round, stage=stage)
        return {
            "season": season, "round": round, "stage": stage,
            "podium": result.get("podium_position_prediction", {}),
            "podium_ranking": result.get("podium_ranking", [])[:5],
            "warnings": result.get("warnings", []),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

---

### PHASE 7 — Wire New Features into Feature Store & Training

#### 7A. Update `src/feature_engineering/feature_store.py` `build()` method

After loading `r_df` and before calling `WeekendFeatureBuilder`, load and merge the new
feature families:

```python
# --- Qualifying Lap Features ---
from src.feature_engineering.qualifying_lap_features import QualifyingLapFeatureBuilder
q_laps_df = self.loader.load_session_laps('Q')  # new DataLoader method
if not q_laps_df.empty:
    qlb = QualifyingLapFeatureBuilder(q_laps_df)
    q_lap_feats = qlb.build_features()
    # merge onto qualifying_features on ['season', 'round', 'driver_code']

# --- Weather Features ---
from src.feature_engineering.weather_features import WeatherFeatureBuilder
r_weather_df = self.loader.load_session_weather('R')  # new DataLoader method
q_weather_df = self.loader.load_session_weather('Q')
# Build weather index: one row per (season, round) with weather_rainfall_flag etc.

# --- Wet Skill Features ---
from src.feature_engineering.wet_skill_features import WetSkillFeatureBuilder
wsb = WetSkillFeatureBuilder(r_df, weather_index)
wet_feats = wsb.build_features()
# merge onto race_features on ['season', 'round', 'driver_code']

# --- Strategy Features ---
from src.feature_engineering.strategy_features import TeamStrategyFeatureBuilder
r_laps_df = self.loader.load_session_laps('R')  # new DataLoader method
tsb = TeamStrategyFeatureBuilder(r_laps_df, r_df)
strategy_feats = tsb.build_features()
# merge onto race_features on ['season', 'round', 'team']
```

#### 7B. Add `load_session_laps()` and `load_session_weather()` to `DataLoader`

```python
def load_session_laps(self, session_type: str) -> pd.DataFrame:
    """Loads and concatenates all *_laps.parquet files for the given session type."""
    ...

def load_session_weather(self, session_type: str) -> pd.DataFrame:
    """Loads and concatenates all *_weather.parquet files for the given session type."""
    ...
```

Both follow the same pattern as `load_session_results()` — glob
`data/processed/sessions/season=*/round=*/{session_type}_laps.parquet` and pd.concat.

#### 7C. Update `scripts/train_advanced.py`

- After the existing `compute_sample_weights()`, update the weights dict:
  ```python
  season_weights = {
      2018: 0.3, 2019: 0.3, 2020: 0.4, 2021: 0.6,
      2022: 1.0, 2023: 2.0, 2024: 3.5,
      2025: 5.0, 2026: 8.0   # 2026 in-season races get 8x weight
  }
  ```
- Call `train_podium_ranker()` for all three stages
- Add a `--stage` argument so individual stages can be retrained without full rebuild:
  ```
  python scripts/train_advanced.py --stage post_qualifying
  ```

---

## Acceptance Criteria

After full implementation, the following must work:

```powershell
# 1. Full automated pre-race run (Canadian GP, after qualifying)
python scripts/pre_race_pipeline.py --season 2026 --round 5

# Expected output:
# PITWALL AI — 2026 Round 5 (POST_QUALIFYING)
# P1 (WINNER) : NOR
# P2          : VER
# P3          : PIA

# 2. API endpoint for podium prediction
curl "http://127.0.0.1:8000/predict/podium?season=2026&round=5&stage=post_qualifying"
# Returns: {"podium": {"P1": "NOR", "P2": "VER", "P3": "PIA"}, ...}

# 3. Feature validation — no leakage
python scripts/audit_feature_inputs.py --season 2026 --round 5 --stage post_qualifying
# Should report 0 leakage violations

# 4. Weather features present
# race_features.parquet for round 5 must have columns:
# weather_rainfall_flag, weather_air_temp_avg, driver_wet_skill_score
```

---

## DO NOT touch

- `tests/conftest.py` — already fixed, do not modify
- `src/modeling/preprocessing.py` `LeakageGuard._check_leakage()` — do not weaken it
- `src/api/prediction_service.py` `_strip_forbidden()` — do not remove this function
- `scripts/generate_upcoming_race_features.py` STEP 9 and STEP 13 — already fixed
- Any existing test in `tests/` that currently passes

---

## Package requirements (add to requirements.txt if missing)

```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
```

---

## Implementation Order

1. Phase 1 (new feature builders) — foundational, everything else depends on these
2. Phase 7B (DataLoader methods) — needed to feed Phase 1 builders
3. Phase 7A (FeatureStore wiring) — connects builders into the pipeline
4. Phase 2 (2026 in-season features) — extend DriverFeatureBuilder
5. Phase 3 (Podium Ranker) — new model, new schema field
6. Phase 4 (News Injector) — isolated, non-breaking addition
7. Phase 5 (Automation scripts) — depends on all above
8. Phase 6 (API endpoints) — final wiring
9. Phase 7C (retrain) — run after all features are wired

Build and test each phase independently before proceeding. Run
`pytest tests/ -x -q` after each phase to catch regressions early.
