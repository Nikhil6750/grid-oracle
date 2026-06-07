"""
Live race prediction router.

Exposes:
    WS  /ws/live/{season}/{round}      - streams predictions every 5s
    GET /live/current/{season}/{round} - REST fallback for a single snapshot

Lap data is sourced (in priority order) from:
    1. The processed parquet (``R_laps.parquet``) for the race  -> REPLAY mode.
    2. OpenF1 live timing when no parquet exists -> LIVE/WAITING/FINISHED mode.

The WebSocket supports many concurrent clients per race: a single background
task per (season, round) "room" polls for new laps, runs the prediction, and
broadcasts the result to every connected client.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.live_prediction import LiveRacePredictor

router = APIRouter()

SESSIONS_DIR = Path("data/processed/sessions")
OPENF1_BASE = "https://api.openf1.org/v1"
BROADCAST_INTERVAL_SECONDS = 5
OPENF1_TIMEOUT_SECONDS = 10
DEFAULT_LAP_SECONDS = 90.0
# In replay mode, advance this many laps per broadcast tick to simulate a race.
REPLAY_LAP_STEP = 3

TOTAL_LAPS_BY_CIRCUIT = {
    "Melbourne": 58,
    "Shanghai": 56,
    "Suzuka": 53,
    "Sakhir": 57,
    "Jeddah": 50,
    "Miami": 57,
    "Montreal": 70,
    "Monte Carlo": 78,
    "Catalunya": 66,
    "Spielberg": 71,
    "Silverstone": 52,
    "Spa-Francorchamps": 44,
    "Hungaroring": 70,
    "Zandvoort": 72,
    "Monza": 53,
    "Madring": 55,
    "Baku": 51,
    "Singapore": 62,
    "Austin": 56,
    "Mexico City": 71,
    "Interlagos": 71,
    "Las Vegas": 50,
    "Lusail": 57,
    "Yas Marina Circuit": 58,
}

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


def _openf1_get(endpoint: str, params: dict) -> list[dict]:
    url = f"{OPENF1_BASE}/{endpoint.lstrip('/')}"
    try:
        res = requests.get(url, params=params, timeout=OPENF1_TIMEOUT_SECONDS)
        if res.status_code == 404:
            return []
        res.raise_for_status()
        payload = res.json()
        return payload if isinstance(payload, list) else []
    except Exception as e:  # pragma: no cover - network/data dependent
        print(f"[live_router] OpenF1 request failed for {url}: {e}")
        return []


def _parse_openf1_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _resolve_openf1_session(season: int, round_num: int) -> dict | None:
    """Resolve the OpenF1 race session for a season/round via /sessions."""
    sessions = _openf1_get("sessions", {"year": season, "session_name": "Race"})
    races = [s for s in sessions if not s.get("is_cancelled")]
    races.sort(key=lambda s: s.get("date_start") or "")
    if 1 <= round_num <= len(races):
        return races[round_num - 1]
    return None


def _total_laps_for_session(session: dict) -> int:
    short_name = session.get("circuit_short_name")
    return TOTAL_LAPS_BY_CIRCUIT.get(short_name, 57)


def _event_name_for_session(session: dict) -> str:
    country = session.get("country_name")
    location = session.get("location")
    if country == "Monaco":
        return "Monaco Grand Prix"
    return f"{location or country or 'OpenF1'} Grand Prix"


def _latest_by_driver(records: list[dict]) -> dict[int, dict]:
    latest: dict[int, dict] = {}
    for rec in records:
        driver_number = rec.get("driver_number")
        if driver_number is None:
            continue
        try:
            key = int(driver_number)
        except (TypeError, ValueError):
            continue
        prev = latest.get(key)
        if prev is None or str(rec.get("date") or "") >= str(prev.get("date") or ""):
            latest[key] = rec
    return latest


def _parse_gap_seconds(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().upper().replace("+", "")
    if not text or "LAP" in text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_gap(value) -> str:
    seconds = _parse_gap_seconds(value)
    if seconds is not None:
        return "LEADER" if seconds == 0 else f"+{seconds:.3f}"
    return str(value) if value not in (None, "") else "--"


def _current_track_status(race_control: list[dict]) -> str:
    for rec in reversed(race_control):
        message = str(rec.get("message") or "").upper()
        flag = str(rec.get("flag") or "").upper()
        if "VIRTUAL SAFETY CAR" in message or flag == "VSC":
            return "VSC"
        if "SAFETY CAR" in message:
            return "SC"
        if flag == "GREEN" or "GREEN" in message:
            return "GREEN"
    return "GREEN"


def _track_status_code(track_status: str) -> str:
    if track_status == "SC":
        return "4"
    if track_status == "VSC":
        return "6"
    return "1"


def _session_status(session: dict, race_control: list[dict]) -> str:
    for rec in reversed(race_control):
        message = str(rec.get("message") or "").upper()
        if "CHEQUERED FLAG" in message or "SESSION FINISHED" in message:
            return "FINISHED"
        if "SESSION STARTED" in message:
            return "LIVE"

    now = datetime.now(timezone.utc)
    start = _parse_openf1_datetime(session.get("date_start"))
    end = _parse_openf1_datetime(session.get("date_end"))
    if start and now < start:
        return "WAITING"
    if end and now > end:
        return "FINISHED"
    return "LIVE"


def _current_lap(stints: list[dict], pits: list[dict], race_control: list[dict], status: str) -> int:
    laps: list[int] = []
    for rec in stints:
        lap = rec.get("lap_end")
        if lap is not None:
            laps.append(int(lap))
    for rec in pits + race_control:
        lap = rec.get("lap_number")
        if lap is not None:
            laps.append(int(lap))
    if laps:
        return max(laps)
    return 1 if status == "LIVE" else 0


def _stints_by_driver(stints: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for rec in stints:
        driver_number = rec.get("driver_number")
        if driver_number is None:
            continue
        grouped.setdefault(int(driver_number), []).append(rec)
    for records in grouped.values():
        records.sort(key=lambda r: (int(r.get("lap_start") or 0), int(r.get("stint_number") or 0)))
    return grouped


def _stint_for_lap(records: list[dict], lap: int) -> dict | None:
    if not records:
        return None
    for rec in records:
        start = int(rec.get("lap_start") or 0)
        end = int(rec.get("lap_end") or start)
        if start <= lap <= end:
            return rec
    return records[-1]


def _build_openf1_laps(
    drivers: list[dict],
    positions: list[dict],
    intervals: list[dict],
    stints: list[dict],
    pits: list[dict],
    race_control: list[dict],
    status: str,
) -> tuple[pd.DataFrame, int, dict[str, dict]]:
    current_lap = _current_lap(stints, pits, race_control, status)
    if current_lap <= 0:
        return pd.DataFrame(columns=["driver_code", "LapNumber"]), current_lap, {}

    driver_codes = {
        int(d["driver_number"]): d.get("name_acronym") or str(d["driver_number"])
        for d in drivers
        if d.get("driver_number") is not None
    }
    latest_positions = _latest_by_driver(positions)
    latest_intervals = _latest_by_driver(intervals)
    stints_grouped = _stints_by_driver(stints)
    pit_laps: dict[int, set[int]] = {}
    for rec in pits:
        if rec.get("driver_number") is None or rec.get("lap_number") is None:
            continue
        pit_laps.setdefault(int(rec["driver_number"]), set()).add(int(rec["lap_number"]))

    track_code = _track_status_code(_current_track_status(race_control))
    rows = []
    gaps: dict[str, dict] = {}
    for driver_number, pos_rec in latest_positions.items():
        code = driver_codes.get(driver_number, str(driver_number))
        position = pos_rec.get("position")
        interval_rec = latest_intervals.get(driver_number, {})
        raw_gap = interval_rec.get("gap_to_leader")
        gap_seconds = _parse_gap_seconds(raw_gap)
        if gap_seconds is None and position == 1:
            gap_seconds = 0.0
        gaps[code] = {
            "gap_to_leader": gap_seconds,
            "gap_to_leader_display": _format_gap(raw_gap if raw_gap is not None else gap_seconds),
        }

        records = stints_grouped.get(driver_number, [])
        for lap in range(1, current_lap + 1):
            stint = _stint_for_lap(records, lap) or {}
            lap_start = int(stint.get("lap_start") or 1)
            tyre_age_start = int(stint.get("tyre_age_at_start") or 0)
            tyre_life = max(tyre_age_start + lap - lap_start + 1, 0)
            elapsed = lap * DEFAULT_LAP_SECONDS
            rows.append({
                "driver_code": code,
                "Driver": code,
                "LapNumber": lap,
                "LapTime": DEFAULT_LAP_SECONDS,
                "Time": elapsed + gap_seconds if gap_seconds is not None else None,
                "Sector1Time": DEFAULT_LAP_SECONDS / 3,
                "Sector2Time": DEFAULT_LAP_SECONDS / 3,
                "Sector3Time": DEFAULT_LAP_SECONDS / 3,
                "Position": position,
                "Compound": stint.get("compound"),
                "TyreLife": tyre_life,
                "Stint": stint.get("stint_number") or 1,
                "PitInTime": elapsed if lap in pit_laps.get(driver_number, set()) else None,
                "TrackStatus": track_code if lap == current_lap else "1",
            })

    return pd.DataFrame(rows), current_lap, gaps


def _load_from_openf1(season: int, round_num: int, session: dict | None = None):
    """Load current race state from OpenF1, or None on failure."""
    session = session or _resolve_openf1_session(season, round_num)
    if not session:
        return None

    session_key = session.get("session_key")
    drivers = _openf1_get("drivers", {"session_key": session_key})
    positions = _openf1_get("position", {"session_key": session_key})
    intervals = _openf1_get("intervals", {"session_key": session_key})
    stints = _openf1_get("stints", {"session_key": session_key})
    pits = _openf1_get("pit", {"session_key": session_key})
    race_control = _openf1_get("race_control", {"session_key": session_key})

    status = _session_status(session, race_control)
    track_status = _current_track_status(race_control)
    laps, current_lap, gaps = _build_openf1_laps(
        drivers,
        positions,
        intervals,
        stints,
        pits,
        race_control,
        status,
    )

    return {
        "laps": laps,
        "total_laps": _total_laps_for_session(session),
        "event_name": _event_name_for_session(session),
        "mode": status,
        "session_status": status,
        "track_status": track_status,
        "session_key": session_key,
        "current_lap": current_lap,
        "gaps": gaps,
    }


def load_race_data(season: int, round_num: int, openf1_session: dict | None = None):
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
    live = _load_from_openf1(season, round_num, openf1_session)
    if live is not None:
        return live
    return None


def build_snapshot(race: dict, lap_n: int) -> dict:
    """Run the predictor for a given lap and wrap it in a broadcast payload."""
    predictor = get_predictor()
    laps = race["laps"]
    total_laps = race["total_laps"]
    lap_n = max(0, min(int(lap_n), total_laps))

    predictions = predictor.predict_from_laps(
        laps,
        lap_n=lap_n,
        total_laps=total_laps,
        event_name=race.get("event_name"),
    )
    gaps = race.get("gaps", {})
    drivers = []
    for code, vals in predictions.items():
        drivers.append({
            "driver_code": code,
            **vals,
            **gaps.get(code, {}),
        })

    return {
        "type": "prediction",
        "mode": race["mode"],
        "session_status": race.get("session_status", race["mode"]),
        "track_status": race.get("track_status", "GREEN"),
        "session_key": race.get("session_key"),
        "event_name": race.get("event_name"),
        "lap_n": lap_n,
        "total_laps": total_laps,
        "pct_complete": round(lap_n / total_laps, 3) if total_laps else 0.0,
        "model_ready": predictor.is_ready,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "drivers": drivers,
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
        self.openf1_session: dict | None = None

    def ensure_openf1_session(self) -> dict | None:
        if self.openf1_session is None:
            self.openf1_session = _resolve_openf1_session(self.season, self.round_num)
        return self.openf1_session

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
        """Background loop: every 5s, advance/poll laps, predict, broadcast."""
        try:
            while self.clients:
                race = load_race_data(self.season, self.round_num, self.ensure_openf1_session())
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
                    self.current_lap = int(race.get("current_lap") or 0)

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
    room.ensure_openf1_session()

    # Send an immediate snapshot so the client renders without waiting 5s.
    race = load_race_data(season, round, room.openf1_session)
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
            room.current_lap = int(race.get("current_lap") or 0)
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
