"""
Live race prediction router.

Exposes:
    WS  /ws/live/{season}/{round}      - streams predictions every 30s
    GET /live/current/{season}/{round} - REST fallback for a single snapshot

Lap data is sourced (in priority order) from:
    1. The processed parquet (``R_laps.parquet``) for the race  -> REPLAY mode.
    2. FastF1 (live timing / session load) when no parquet exists -> LIVE mode.

The WebSocket supports many concurrent clients per race: a single background
task per (season, round) "room" polls for new laps, runs the prediction, and
broadcasts the result to every connected client.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.live_prediction import LiveRacePredictor

router = APIRouter()

SESSIONS_DIR = Path("data/processed/sessions")
BROADCAST_INTERVAL_SECONDS = 30
# In replay mode, advance this many laps per broadcast tick to simulate a race.
REPLAY_LAP_STEP = 3

# Shared predictor (models load once).
_predictor: LiveRacePredictor | None = None


def get_predictor() -> LiveRacePredictor:
    global _predictor
    if _predictor is None:
        _predictor = LiveRacePredictor()
    return _predictor


# --------------------------------------------------------------------------- #
# Data sourcing
# --------------------------------------------------------------------------- #
def _read_event_name(race_dir: Path) -> str | None:
    for fname in ("R_session_metadata.json", "event_manifest.json"):
        fpath = race_dir / fname
        if fpath.exists():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    return json.load(f).get("event_name")
            except Exception:
                continue
    return None


def _load_from_processed(season: int, round_num: int):
    """Return (laps_df, total_laps, event_name) from local parquet, or None."""
    race_dir = SESSIONS_DIR / f"season={season}" / f"round={round_num:02d}"
    laps_path = race_dir / "R_laps.parquet"
    if not laps_path.exists():
        # Some folders may not zero-pad the round.
        race_dir = SESSIONS_DIR / f"season={season}" / f"round={round_num}"
        laps_path = race_dir / "R_laps.parquet"
    if not laps_path.exists():
        return None
    try:
        laps = pd.read_parquet(laps_path)
    except Exception:
        return None
    if laps.empty or "LapNumber" not in laps.columns:
        return None
    total_laps = int(pd.to_numeric(laps["LapNumber"], errors="coerce").max())
    return laps, total_laps, _read_event_name(race_dir)


def _load_from_fastf1(season: int, round_num: int):
    """Attempt to load laps from FastF1 (live/recent), or None on failure."""
    try:
        import fastf1
        from src.utils.paths import FASTF1_CACHE_DIR

        FASTF1_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(FASTF1_CACHE_DIR))
        session = fastf1.get_session(season, round_num, "R")
        session.load(laps=True, telemetry=False, weather=False, messages=False)
        laps = session.laps
        if laps is None or laps.empty:
            return None
        laps = laps.copy()
        # Convert timedeltas to seconds to match the parquet schema.
        for col in ["LapTime", "Sector1Time", "Sector2Time", "Sector3Time",
                    "Time", "PitInTime", "PitOutTime", "LapStartTime"]:
            if col in laps.columns and pd.api.types.is_timedelta64_dtype(laps[col]):
                laps[col] = laps[col].dt.total_seconds()
        total_laps = int(pd.to_numeric(laps["LapNumber"], errors="coerce").max())
        event_name = getattr(session.event, "EventName", None) if hasattr(session, "event") else None
        return laps, total_laps, event_name
    except Exception as e:  # pragma: no cover - network/data dependent
        print(f"[live_router] FastF1 load failed for {season} R{round_num}: {e}")
        return None


def load_race_data(season: int, round_num: int):
    """Return dict with laps/total_laps/event_name/mode, or None if unavailable."""
    processed = _load_from_processed(season, round_num)
    if processed is not None:
        laps, total_laps, event_name = processed
        return {
            "laps": laps,
            "total_laps": total_laps,
            "event_name": event_name,
            "mode": "REPLAY",
        }
    live = _load_from_fastf1(season, round_num)
    if live is not None:
        laps, total_laps, event_name = live
        return {
            "laps": laps,
            "total_laps": total_laps,
            "event_name": event_name,
            "mode": "LIVE",
        }
    return None


def build_snapshot(race: dict, lap_n: int) -> dict:
    """Run the predictor for a given lap and wrap it in a broadcast payload."""
    predictor = get_predictor()
    laps = race["laps"]
    total_laps = race["total_laps"]
    lap_n = max(1, min(int(lap_n), total_laps))

    predictions = predictor.predict_from_laps(
        laps,
        lap_n=lap_n,
        total_laps=total_laps,
        event_name=race.get("event_name"),
    )
    return {
        "type": "prediction",
        "mode": race["mode"],
        "event_name": race.get("event_name"),
        "lap_n": lap_n,
        "total_laps": total_laps,
        "pct_complete": round(lap_n / total_laps, 3) if total_laps else 0.0,
        "model_ready": predictor.is_ready,
        "drivers": [{"driver_code": code, **vals} for code, vals in predictions.items()],
    }


# --------------------------------------------------------------------------- #
# Connection management (multi-client rooms)
# --------------------------------------------------------------------------- #
class RaceRoom:
    """Holds the connected clients and broadcaster task for one race."""

    def __init__(self, season: int, round_num: int):
        self.season = season
        self.round_num = round_num
        self.clients: set[WebSocket] = set()
        self.task: asyncio.Task | None = None
        self.current_lap = 1

    async def broadcast(self, message: dict) -> None:
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    async def run(self) -> None:
        """Background loop: every 30s, advance/poll laps, predict, broadcast."""
        try:
            while self.clients:
                race = load_race_data(self.season, self.round_num)
                if race is None:
                    await self.broadcast({
                        "type": "error",
                        "message": f"No data for {self.season} R{self.round_num}",
                    })
                    await asyncio.sleep(BROADCAST_INTERVAL_SECONDS)
                    continue

                total_laps = race["total_laps"]
                if race["mode"] == "REPLAY":
                    # Simulate race progression.
                    self.current_lap = min(self.current_lap + REPLAY_LAP_STEP, total_laps)
                else:
                    # LIVE: current lap is the latest completed lap available.
                    self.current_lap = total_laps

                snapshot = build_snapshot(race, self.current_lap)
                await self.broadcast(snapshot)

                if race["mode"] == "REPLAY" and self.current_lap >= total_laps:
                    await self.broadcast({"type": "complete", "lap_n": self.current_lap})
                    break

                await asyncio.sleep(BROADCAST_INTERVAL_SECONDS)
        except asyncio.CancelledError:  # pragma: no cover
            pass


class RoomManager:
    def __init__(self):
        self.rooms: dict[tuple[int, int], RaceRoom] = {}

    def get_room(self, season: int, round_num: int) -> RaceRoom:
        key = (season, round_num)
        if key not in self.rooms:
            self.rooms[key] = RaceRoom(season, round_num)
        return self.rooms[key]

    async def connect(self, ws: WebSocket, season: int, round_num: int) -> RaceRoom:
        await ws.accept()
        room = self.get_room(season, round_num)
        room.clients.add(ws)
        return room

    def disconnect(self, ws: WebSocket, room: RaceRoom) -> None:
        room.clients.discard(ws)
        if not room.clients and room.task is not None:
            room.task.cancel()
            room.task = None


manager = RoomManager()


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@router.websocket("/ws/live/{season}/{round}")
async def live_predictions_ws(websocket: WebSocket, season: int, round: int):
    room = await manager.connect(websocket, season, round)

    # Send an immediate snapshot so the client renders without waiting 30s.
    race = load_race_data(season, round)
    if race is None:
        await websocket.send_json({
            "type": "error",
            "message": f"No data available for {season} R{round}",
        })
    else:
        if race["mode"] == "REPLAY":
            # Start the replay at a meaningful point rather than lap 1.
            room.current_lap = max(room.current_lap, min(10, race["total_laps"]))
        else:
            room.current_lap = race["total_laps"]
        await websocket.send_json(build_snapshot(race, room.current_lap))

    # Launch the shared broadcaster for this room if not already running.
    if room.task is None or room.task.done():
        room.task = asyncio.create_task(room.run())

    try:
        while True:
            # Keep the connection alive; ignore/echo client pings.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
    except Exception:
        manager.disconnect(websocket, room)


@router.get("/live/current/{season}/{round}")
def live_current(season: int, round: int, lap_n: int | None = None):
    """REST fallback: returns a single prediction snapshot."""
    race = load_race_data(season, round)
    if race is None:
        return {
            "type": "error",
            "message": f"No data available for {season} R{round}",
            "drivers": [],
        }
    target_lap = lap_n if lap_n is not None else race["total_laps"]
    return build_snapshot(race, target_lap)
