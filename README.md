# PitWall AI — F1 Race Intelligence Backend

PitWall AI is a production-grade Formula 1 prediction backend. 
It predicts race outcomes, qualifying order, sprint results, and more using advanced tabular models.

## Backend MVP Status
*   **Feature Store**: Functional. Ingests data from 2018–2024.
*   **Baseline Models**: Functional (RandomForest/LogisticRegression).
*   **Advanced Models**: Functional (HistGradientBoosting), though currently in early iterations. *Note: Due to small dataset size and regularization, some naive baselines may currently outperform advanced models on test sets.*
*   **REST API**: Available. Exposes health and prediction endpoints.

## Installation

```bash
# Create virtual environment (Python 3.11+ recommended)
python -m venv .venv

# Activate it
# Windows:
.\.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
pip install fastapi uvicorn httpx

# Create .env from example
cp .env.example .env

# Initialize directories and FastF1 cache
python scripts/setup_cache.py

# Run tests
pytest
```

## Running the API

You can start the backend API using the provided runner script:

```bash
python scripts/run_api.py --port 8000
```

Once running, the interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### Endpoints

#### Health Check
```bash
curl http://127.0.0.1:8000/health
```

#### Prediction Endpoint
Get predictions for a specific race and stage (`pre_weekend` or `post_qualifying`).

**Example: 2024 Miami Grand Prix (Round 6) - Pre-Weekend Prediction**
```bash
curl "http://127.0.0.1:8000/predict/race?season=2024&round=6&stage=pre_weekend"
```

For more detailed API documentation and example responses, see `docs/API.md`.
