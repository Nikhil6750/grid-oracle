from pydantic import BaseModel
from typing import Optional

class DriverPrediction(BaseModel):
    driver: str
    probability: float

class ModelsUsed(BaseModel):
    qualifying: Optional[str] = None
    race_finish: Optional[str] = None
    podium: Optional[str] = None
    podium_ranker: Optional[str] = None
    top10: Optional[str] = None

class PredictionResponse(BaseModel):
    season: int
    round: int
    stage: str
    pole_sitter_candidate: Optional[str] = None
    race_winner_candidate: Optional[str] = None
    podium_ranking: list[DriverPrediction] = []
    podium_position_prediction: dict[str, str] = {}
    top10_ranking: list[DriverPrediction] = []
    models_used: ModelsUsed = ModelsUsed()
    warnings: list[str] = []
    prediction_records_path: str = "reports/advanced_predictions.parquet"

class HealthResponse(BaseModel):
    status: str
    service: str

class ErrorResponse(BaseModel):
    detail: str
