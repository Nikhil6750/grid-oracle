# PitWall AI — Automated F1 Race Prediction Engine

## Overview
Automated pre-race prediction system for Formula 1. Ingests live session data via FastF1, builds rolling driver/team/circuit/weather features, and outputs P1/P2/P3 podium predictions before lights out. Designed for the 2026 season with heavy recency weighting and live news injection for grid penalties and weather alerts.

## Architecture
```text
FastF1 API -> Ingestor -> Feature Store -> Model Pipeline -> REST API -> Frontend
```

## Feature Families
* Historical driver stats (rolling 3/5 race windows, shift(1) leakage-safe)
* Qualifying lap detail (gap to pole, sector times, session reached)
* Weather (rainfall flag, track/air temp, humidity, wind)
* Driver wet-skill ratings (wet vs dry delta, rolling wet podium rate)
* Team strategy DNA (pit stop consistency, undercut/overcut frequency)
* 2026 in-season form (season last-3 finish, momentum, quali consistency)
* Live news injection (grid penalties, wet race probability)

## Models
* HistGradientBoostingRegressor for race finish position and qualifying
* HistGradientBoostingClassifier for podium (binary) and top-10
* RandomForestClassifier (Podium Position Ranker) for exact P1/P2/P3
* All trained per stage: pre_weekend, post_qualifying, post_sprint
* 2026 sample weight: 8x vs 0.3x for 2018 data

## Quick Start
```bash
# Install
pip install -r requirements.txt

# Run the full pre-race pipeline (auto-detects stage)
python scripts/pre_race_pipeline.py --season 2026 --round 5

# Start the API
uvicorn src.api.main:app --reload
```

```http
# API endpoints
GET  /predict/race?season=2026&round=5&stage=post_qualifying
GET  /predict/podium?season=2026&round=5&stage=post_qualifying
POST /ingest/session?season=2026&round=5&session=Q
```

## Weekend Run Schedule
| When | Command | Stage |
| --- | --- | --- |
| After qualifying | `pre_race_pipeline.py --round N` | post_qualifying |
| After sprint | `pre_race_pipeline.py --round N` | post_sprint |
| Race day | `/predict/podium` API | Final P1/P2/P3 |

## Data Pipeline
Data stored in `data/processed/sessions/season=YYYY/round=RR/`
Features written to `data/features/race_features.parquet`
Models saved to `models/advanced/*.joblib`

## Leakage Safety
All feature builders use `shift(1)` to ensure round-N features only use rounds 1..N-1. LeakageGuard in the sklearn pipeline rejects any forbidden column (race_finish_position, points, etc.) at both training and inference time. Inference additionally strips target columns via `_strip_forbidden()`.

## Tech Stack
Python 3.11 · FastAPI · FastF1 · scikit-learn · pandas · React/Vite
