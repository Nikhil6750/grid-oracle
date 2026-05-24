# PitWall AI — Automated F1 Race Prediction Engine
Live pre-race podium prediction powered by FastF1, sklearn, and FastAPI.

## Overview
Automated pre-race prediction system for Formula 1. Ingests live F1 session data via FastF1, builds rolling driver/team/weather/strategy features, and outputs P1/P2/P3 podium predictions before lights out. Heavily weighted toward 2026 in-season form with live news injection for grid penalties and weather alerts.

## Architecture
```text
FastF1 API -> Ingestor -> Feature Store -> Model Pipeline -> REST API -> React Frontend
```

## Feature Families
* Historical driver stats (rolling 3/5 race windows, shift(1) leakage-safe)
* Qualifying lap detail (gap to pole, sector times, session reached, consistency)
* Weather (rainfall flag, track/air temp, humidity, wind speed)
* Driver wet-skill ratings (wet vs dry delta, rolling wet podium rate)
* Team strategy DNA (pit stop consistency, undercut/overcut frequency, tyre preference)
* 2026 in-season form (last-3 finish avg, momentum trend, quali consistency)
* Live news injection (grid penalties, wet race probability from F1 feeds)

## Models
* HistGradientBoostingRegressor: race finish position, qualifying position
* HistGradientBoostingClassifier: podium binary, top-10 binary
* RandomForestClassifier (Podium Ranker): exact P1/P2/P3 from top-5 candidates
* Trained per stage: pre_weekend, post_qualifying, post_sprint
* Sample weights: 2026 = 8x, 2018 = 0.3x

## Quick Start
```bash
pip install -r requirements.txt
python scripts/pre_race_pipeline.py --season 2026 --round 6
uvicorn src.api.main:app --reload
```

## Key API Endpoints
```http
GET  /predict/race?season=2026&round=6&stage=post_qualifying
GET  /predict/podium?season=2026&round=6&stage=post_qualifying
POST /ingest/session?season=2026&round=6&session=Q
```

## Weekend Run Schedule
| Timing | Command | Stage |
| --- | --- | --- |
| Pre-weekend | `pre_race_pipeline.py --round N` | pre_weekend |
| After qualifying | `pre_race_pipeline.py --round N` | post_qualifying |
| After sprint | `pre_race_pipeline.py --round N` | post_sprint |

## Data Layout
* `data/processed/sessions/season=YYYY/round=RR/` — raw FastF1 parquets
* `data/features/race_features.parquet` — assembled feature store
* `models/advanced/*.joblib` — trained sklearn pipelines

## Leakage Safety
All feature builders follow strict `shift(1)` discipline to ensure round-N features only use rounds 1..N-1. A `LeakageGuard` in the sklearn pipeline rejects any forbidden column at both training and inference time. Inference additionally strips target columns via `_strip_forbidden()`.

## Tech Stack
Python 3.11, FastAPI, FastF1, scikit-learn, pandas, React/Vite
