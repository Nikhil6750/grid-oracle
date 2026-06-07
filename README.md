# PitWall AI — F1 Race Intelligence System 🏎️🔮

> ML-powered Formula 1 prediction system with live race tracking. PitWall AI forecasts podium finishers from qualifying data and updates win/podium probabilities in real time as a race unfolds.

---

## ✨ Features

- **Post-qualifying podium prediction** — XGBoost ensemble that estimates the likely top 3 finishers once the grid is set.
- **Live race prediction** — win/podium probabilities that refresh every 5 seconds using live timing from the OpenF1 API.
- **Wet race specialist model** — a dedicated model that takes over when rain is forecast or detected.
- **Street circuit modifier** — adjusts predictions for the unique characteristics of street tracks (Monaco, Miami, etc.).
- **React frontend** — responsive dashboard with a live timing leaderboard and prediction panel.

---

## 🛠️ Tech Stack

- **Backend / ML**: Python 3.11, FastAPI, FastF1, XGBoost, scikit-learn, pandas, NumPy
- **Frontend**: React + Vite
- **Data Sources**: FastF1 (historical & session data), OpenF1 API (live timing)
- **Serving**: Uvicorn

---

## 📦 Installation

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in any required values.

### Frontend

```bash
cd frontend
npm install
```

---

## 🚀 Running

### Backend API

```bash
python scripts/run_api.py --port 8000 --reload
```

Or run Uvicorn directly:

```bash
uvicorn src.api.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000` (interactive docs at `/docs`).

### Frontend

```bash
cd frontend
npm run dev
```

---

## 🔌 API Endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET`  | `/health` | Health check. |
| `GET`  | `/predict/race?season={year}&round={n}&stage={stage}` | Race outcome prediction. `stage` is one of `pre_weekend`, `post_qualifying`, `post_sprint`. |
| `GET`  | `/predict/podium?season={year}&round={n}&stage={stage}` | Podium (top 3) prediction. |
| `POST` | `/ingest/session` | Trigger background session ingestion and the pre-race pipeline. |
| `GET`  | `/live/current/{season}/{round}` | Live race prediction, updated from OpenF1 timing. |

---

## 📂 Project Structure

```text
pitwall-ai-backend/
├── frontend/        # React + Vite frontend (live timing leaderboard + prediction UI)
├── src/             # Backend and ML source code
│   └── api/         # FastAPI app, live prediction router, prediction service
├── scripts/         # Training, ingestion, feature-build, and run scripts
├── models/          # Trained model artifacts (.joblib, git-ignored)
├── data/            # Raw, processed, and feature data
├── reports/         # Generated reports and outputs
├── tests/           # Test suite
├── requirements.txt # Python dependencies
└── README.md
```

---

## 👤 Author

**Nikhil Reddy** — [GitHub](https://github.com/Nikhil6750)
