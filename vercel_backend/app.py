"""
Lightweight FastAPI entrypoint for Vercel deployment.
No heavy ML dependencies — safe to bundle within Vercel's 245 MB limit.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

app = FastAPI(
    title="Grid Oracle Backend",
    description="Lightweight F1 prediction API for Vercel deployment.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://grid-oracle-nine.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "Grid Oracle lightweight backend is running"}


class PredictPayload(BaseModel):
    data: Any = None


@app.post("/predict")
def predict(payload: PredictPayload):
    return {
        "message": "Prediction API is live",
        "note": "Heavy ML prediction is not enabled on Vercel lightweight backend yet",
        "input_received": payload.data,
    }

# trigger redeploy
