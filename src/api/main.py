"""
PitWall AI — FastAPI Backend MVP
"""
from fastapi import FastAPI, Query, HTTPException
from src.api.schemas import PredictionResponse, HealthResponse, ErrorResponse
from src.api.prediction_service import run_prediction

app = FastAPI(
    title="PitWall AI Backend",
    description="F1 race prediction API powered by advanced tabular models.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", service="PitWall AI Backend")


@app.get(
    "/predict/race",
    response_model=PredictionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        404: {"model": ErrorResponse, "description": "Race data not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
def predict_race(
    season: int = Query(..., ge=2018, le=2030, description="Season year"),
    round: int = Query(..., ge=1, le=30, description="Round number"),
    stage: str = Query(..., description="Prediction stage: pre_weekend or post_qualifying"),
):
    # Validate stage
    valid_stages = ["pre_weekend", "post_qualifying"]
    if stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage '{stage}'. Must be one of: {valid_stages}",
        )

    try:
        result = run_prediction(season=season, round_num=round, stage=stage)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return PredictionResponse(**result)
