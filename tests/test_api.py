import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add src to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.api.main import app

client = TestClient(app)


def test_health():
    """GET /health returns 200 with expected fields."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "PitWall AI Backend"


def test_predict_race_returns_expected_keys():
    """GET /predict/race with valid params returns all expected keys."""
    response = client.get("/predict/race", params={
        "season": 2024, "round": 6, "stage": "pre_weekend"
    })
    assert response.status_code == 200
    data = response.json()
    assert "season" in data
    assert "round" in data
    assert "stage" in data
    assert "pole_sitter_candidate" in data
    assert "race_winner_candidate" in data
    assert "podium_ranking" in data
    assert "top10_ranking" in data
    assert "models_used" in data
    assert "warnings" in data
    assert data["season"] == 2024
    assert data["round"] == 6
    assert data["stage"] == "pre_weekend"


def test_predict_race_post_qualifying():
    """GET /predict/race with post_qualifying stage works and has no pole sitter."""
    response = client.get("/predict/race", params={
        "season": 2024, "round": 6, "stage": "post_qualifying"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["pole_sitter_candidate"] is None
    assert len(data["top10_ranking"]) == 10


def test_predict_race_podium_top5():
    """Podium ranking has at most 5 entries."""
    response = client.get("/predict/race", params={
        "season": 2024, "round": 6, "stage": "pre_weekend"
    })
    data = response.json()
    assert len(data["podium_ranking"]) <= 5


def test_predict_race_top10_exactly_10():
    """Top 10 ranking has exactly 10 entries."""
    response = client.get("/predict/race", params={
        "season": 2024, "round": 6, "stage": "pre_weekend"
    })
    data = response.json()
    assert len(data["top10_ranking"]) == 10


def test_invalid_stage_returns_400():
    """Invalid stage returns HTTP 400."""
    response = client.get("/predict/race", params={
        "season": 2024, "round": 6, "stage": "invalid_stage"
    })
    assert response.status_code == 400
    data = response.json()
    assert "Invalid stage" in data["detail"]


def test_missing_race_returns_404():
    """Non-existent race returns HTTP 404."""
    response = client.get("/predict/race", params={
        "season": 2099, "round": 99, "stage": "pre_weekend"
    })
    # season 2099 will be rejected by validation (ge=2018, le=2030)
    assert response.status_code == 422  # Pydantic validation error


def test_missing_round_data_returns_404():
    """Valid season but round with no data returns 404."""
    response = client.get("/predict/race", params={
        "season": 2024, "round": 30, "stage": "pre_weekend"
    })
    assert response.status_code == 404


def test_predict_race_models_used_keys():
    """models_used has the expected structure."""
    response = client.get("/predict/race", params={
        "season": 2024, "round": 6, "stage": "pre_weekend"
    })
    data = response.json()
    models = data["models_used"]
    assert "qualifying" in models
    assert "race_finish" in models
    assert "podium" in models
    assert "top10" in models
