"""
PitWall AI — FastAPI Backend MVP
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.api.schemas import PredictionResponse, HealthResponse, ErrorResponse
from src.api.prediction_service import run_prediction
import subprocess
from pydantic import BaseModel

app = FastAPI(
    title="PitWall AI Backend",
    description="F1 race prediction API powered by advanced tabular models.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://grid-oracle-nine.vercel.app/",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    valid_stages = ["pre_weekend", "post_qualifying", "post_sprint"]
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

class IngestRequest(BaseModel):
    season: int
    round: int
    session: str = None
    force: bool = False

@app.post("/ingest/session")
def ingest_session_endpoint(req: IngestRequest):
    """Triggers background session ingestion and pipeline steps."""
    cmd = ["python", "scripts/pre_race_pipeline.py", "--season", str(req.season), "--round", str(req.round)]
    if req.force:
        # Pass force if we want to rebuild features
        pass
    
    # Ideally this runs as a background task, but for MVP we run synchronously or just return accepted.
    import threading
    def _run_pipeline():
        subprocess.run(cmd, capture_output=True)
        
    t = threading.Thread(target=_run_pipeline)
    t.start()
    return {"status": "accepted", "message": f"Ingestion pipeline started for {req.season} R{req.round}"}


@app.get(
    "/predict/podium",
    response_model=PredictionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        404: {"model": ErrorResponse, "description": "Race data not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
def predict_podium(
    season: int = Query(..., ge=2018, le=2030, description="Season year"),
    round: int = Query(..., ge=1, le=30, description="Round number"),
    stage: str = Query(..., description="Prediction stage: pre_weekend, post_qualifying, post_sprint"),
):
    valid_stages = ["pre_weekend", "post_qualifying", "post_sprint"]
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