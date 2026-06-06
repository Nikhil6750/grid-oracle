"""
Mid-race feature engineering for the live race prediction system.

Given the lap-by-lap data available *up to a given lap N*, this builder computes
per-driver features that describe the current race situation without ever using
any information from after lap N. The resulting features feed the live models in
``models/live/`` to predict each driver's final finishing position.

LeakageGuard: this module only ever reads laps with ``LapNumber <= lap_n``. The
final finishing position is *never* computed here — it is attached separately as
a target by ``scripts/build_mid_race_features.py``.

Follows the existing ``src/feature_engineering`` conventions: a small builder
class, graceful NaN handling, and ``*_missing`` indicator columns.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Compound -> ordinal encoding. Softer (faster, higher deg) -> lower number.
COMPOUND_ENCODING = {
    "SOFT": 1.0,
    "MEDIUM": 2.0,
    "HARD": 3.0,
    "INTERMEDIATE": 4.0,
    "WET": 5.0,
}

# Track status codes that indicate a neutralised track (FastF1 / F1 timing):
#   4 = Safety Car, 5 = Red Flag, 6 = Virtual Safety Car, 7 = VSC ending.
# TrackStatus values can be concatenations of several codes within one sample
# (e.g. "12", "67"), so we test for membership of any neutralising digit.
SAFETY_CAR_DIGITS = {"4", "6", "7"}

# Circuits run on public roads. Used for the ``is_street_circuit`` flag when an
# explicit value is not supplied. Matched as case-insensitive substrings of the
# event name.
STREET_CIRCUIT_KEYWORDS = (
    "monaco",
    "singapore",
    "azerbaijan",
    "baku",
    "saudi",
    "jeddah",
    "las vegas",
    "vegas",
    "miami",
)

# Numeric feature columns produced for every driver. Each gets a matching
# ``<name>_missing`` indicator when the underlying value could not be computed.
FEATURE_COLUMNS = [
    "current_position",
    "laps_remaining",
    "pct_race_complete",
    "avg_lap_time_last5",
    "lap_time_trend",
    "best_lap_time",
    "tyre_compound",
    "tyre_life",
    "pit_stops_done",
    "positions_gained_from_start",
    "position_trend_last3",
    "gap_to_leader",
    "safety_car_laps",
    "sector1_avg_last3",
    "sector2_avg_last3",
    "sector3_avg_last3",
    "is_street_circuit",
]

# Sensible neutral fill values used when a feature cannot be computed for a
# driver (e.g. they have not completed enough laps yet).
_FILL_DEFAULTS = {
    "current_position": 20.0,
    "laps_remaining": 0.0,
    "pct_race_complete": 0.0,
    "avg_lap_time_last5": 0.0,
    "lap_time_trend": 0.0,
    "best_lap_time": 0.0,
    "tyre_compound": 2.0,
    "tyre_life": 0.0,
    "pit_stops_done": 0.0,
    "positions_gained_from_start": 0.0,
    "position_trend_last3": 0.0,
    "gap_to_leader": 0.0,
    "safety_car_laps": 0.0,
    "sector1_avg_last3": 0.0,
    "sector2_avg_last3": 0.0,
    "sector3_avg_last3": 0.0,
    "is_street_circuit": 0.0,
}


class MidRaceFeatureBuilder:
    """Builds per-driver features from the lap data available at a given lap.

    Parameters
    ----------
    laps_df:
        Lap-by-lap data for a *single* race (the ``R_laps.parquet`` schema).
        May use either ``Driver`` or ``driver_code`` for the driver identifier.
    total_laps:
        Scheduled number of laps in the race. If ``None`` it is inferred from
        the maximum ``LapNumber`` present in ``laps_df``.
    is_street_circuit:
        Explicit street-circuit flag. If ``None`` it is inferred from
        ``event_name`` using :data:`STREET_CIRCUIT_KEYWORDS`.
    event_name:
        Optional event name, used only to infer ``is_street_circuit``.
    """

    def __init__(
        self,
        laps_df: pd.DataFrame,
        total_laps: int | None = None,
        is_street_circuit: bool | None = None,
        event_name: str | None = None,
    ):
        self.laps = self._standardise(laps_df)

        if total_laps is not None and total_laps > 0:
            self.total_laps = int(total_laps)
        elif not self.laps.empty and self.laps["LapNumber"].notna().any():
            self.total_laps = int(self.laps["LapNumber"].max())
        else:
            self.total_laps = 0

        if is_street_circuit is not None:
            self.is_street_circuit = bool(is_street_circuit)
        else:
            self.is_street_circuit = self._infer_street_circuit(event_name)

    # ------------------------------------------------------------------ #
    # Setup helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _standardise(laps_df: pd.DataFrame) -> pd.DataFrame:
        """Return a copy with a guaranteed ``driver_code`` column and numerics."""
        if laps_df is None or laps_df.empty:
            return pd.DataFrame(columns=["driver_code", "LapNumber"])

        df = laps_df.copy()
        if "driver_code" not in df.columns:
            if "Driver" in df.columns:
                df["driver_code"] = df["Driver"].astype(str)
            else:
                raise ValueError("laps_df must contain a 'Driver' or 'driver_code' column")
        else:
            df["driver_code"] = df["driver_code"].astype(str)

        numeric_cols = [
            "LapNumber", "LapTime", "TyreLife", "Position", "Time",
            "Sector1Time", "Sector2Time", "Sector3Time", "PitInTime", "Stint",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "TrackStatus" in df.columns:
            df["TrackStatus"] = df["TrackStatus"].astype(str)

        return df

    @staticmethod
    def _infer_street_circuit(event_name: str | None) -> bool:
        if not event_name:
            return False
        name = str(event_name).lower()
        return any(kw in name for kw in STREET_CIRCUIT_KEYWORDS)

    # ------------------------------------------------------------------ #
    # Safety car (race-wide, identical for every driver)
    # ------------------------------------------------------------------ #
    def _safety_car_laps(self, lap_n: int) -> float:
        if self.laps.empty or "TrackStatus" not in self.laps.columns:
            return 0.0
        upto = self.laps[self.laps["LapNumber"] <= lap_n]
        if upto.empty:
            return 0.0
        sc_laps = set()
        for lap_num, status in zip(upto["LapNumber"], upto["TrackStatus"]):
            if pd.isna(lap_num):
                continue
            if any(d in str(status) for d in SAFETY_CAR_DIGITS):
                sc_laps.add(int(lap_num))
        return float(len(sc_laps))

    def _leader_time_at_lap(self, lap_n: int) -> float | None:
        """Best (minimum) cumulative ``Time`` recorded on the leading lap <= lap_n."""
        if "Time" not in self.laps.columns:
            return None
        upto = self.laps[(self.laps["LapNumber"] <= lap_n) & self.laps["Time"].notna()]
        if upto.empty:
            return None
        max_lap = upto["LapNumber"].max()
        on_lead_lap = upto[upto["LapNumber"] == max_lap]
        if on_lead_lap.empty:
            return None
        return float(on_lead_lap["Time"].min())

    # ------------------------------------------------------------------ #
    # Per-driver feature computation
    # ------------------------------------------------------------------ #
    def _driver_features(self, driver_laps: pd.DataFrame, lap_n: int) -> dict:
        """Compute the raw feature dict for one driver (NaN where unknown)."""
        feats: dict = {}

        # Completed laps only, in lap order.
        dl = driver_laps[driver_laps["LapNumber"] <= lap_n].sort_values("LapNumber")
        green = dl[dl["LapTime"].notna()] if "LapTime" in dl.columns else dl

        # --- position --------------------------------------------------- #
        pos_series = dl["Position"].dropna() if "Position" in dl.columns else pd.Series(dtype=float)
        current_position = float(pos_series.iloc[-1]) if not pos_series.empty else np.nan
        start_position = float(pos_series.iloc[0]) if not pos_series.empty else np.nan
        feats["current_position"] = current_position

        # --- race progress (race-wide) ---------------------------------- #
        laps_remaining = max(self.total_laps - lap_n, 0) if self.total_laps else np.nan
        feats["laps_remaining"] = float(laps_remaining) if laps_remaining == laps_remaining else np.nan
        feats["pct_race_complete"] = (
            float(lap_n) / self.total_laps if self.total_laps else np.nan
        )

        # --- lap pace --------------------------------------------------- #
        lap_times = green["LapTime"].dropna() if "LapTime" in green.columns else pd.Series(dtype=float)
        if not lap_times.empty:
            feats["avg_lap_time_last5"] = float(lap_times.tail(5).mean())
            feats["best_lap_time"] = float(lap_times.min())
        else:
            feats["avg_lap_time_last5"] = np.nan
            feats["best_lap_time"] = np.nan

        # Trend: slope of a linear fit over the last 5 green laps (s/lap).
        # Positive => slowing down (degradation), negative => improving.
        recent = lap_times.tail(5)
        if len(recent) >= 2:
            x = np.arange(len(recent), dtype=float)
            slope = np.polyfit(x, recent.to_numpy(dtype=float), 1)[0]
            feats["lap_time_trend"] = float(slope)
        else:
            feats["lap_time_trend"] = np.nan

        # --- tyres ------------------------------------------------------ #
        if "Compound" in dl.columns and not dl["Compound"].dropna().empty:
            compound = str(dl["Compound"].dropna().iloc[-1]).upper()
            feats["tyre_compound"] = COMPOUND_ENCODING.get(compound, np.nan)
        else:
            feats["tyre_compound"] = np.nan

        if "TyreLife" in dl.columns and not dl["TyreLife"].dropna().empty:
            feats["tyre_life"] = float(dl["TyreLife"].dropna().iloc[-1])
        else:
            feats["tyre_life"] = np.nan

        # --- pit stops -------------------------------------------------- #
        if "PitInTime" in dl.columns:
            feats["pit_stops_done"] = float(dl["PitInTime"].notna().sum())
        elif "Stint" in dl.columns and not dl["Stint"].dropna().empty:
            feats["pit_stops_done"] = float(dl["Stint"].dropna().nunique() - 1)
        else:
            feats["pit_stops_done"] = np.nan

        # --- position dynamics ----------------------------------------- #
        if current_position == current_position and start_position == start_position:
            feats["positions_gained_from_start"] = start_position - current_position
        else:
            feats["positions_gained_from_start"] = np.nan

        if len(pos_series) >= 4:
            past = float(pos_series.iloc[-4])  # position 3 laps ago
            feats["position_trend_last3"] = past - current_position
        else:
            feats["position_trend_last3"] = np.nan

        # --- gap to leader (from cumulative lap time) ------------------- #
        leader_time = self._leader_time_at_lap(lap_n)
        driver_time = np.nan
        if "Time" in dl.columns:
            dt = dl["Time"].dropna()
            if not dt.empty:
                driver_time = float(dt.iloc[-1])
        if leader_time is not None and driver_time == driver_time:
            feats["gap_to_leader"] = max(driver_time - leader_time, 0.0)
        else:
            feats["gap_to_leader"] = np.nan

        # --- sector averages (last 3 laps) ------------------------------ #
        for i in (1, 2, 3):
            col = f"Sector{i}Time"
            if col in green.columns and not green[col].dropna().empty:
                feats[f"sector{i}_avg_last3"] = float(green[col].dropna().tail(3).mean())
            else:
                feats[f"sector{i}_avg_last3"] = np.nan

        return feats

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def build_features_at_lap(self, lap_n: int) -> pd.DataFrame:
        """Return a DataFrame of per-driver features as of ``lap_n``.

        The returned frame has one row per driver with a ``driver_code`` column,
        the columns in :data:`FEATURE_COLUMNS`, and a ``<name>_missing``
        indicator (1.0 where the value had to be imputed) for each feature.
        """
        if self.laps.empty:
            cols = ["driver_code"] + FEATURE_COLUMNS + [f"{c}_missing" for c in FEATURE_COLUMNS]
            return pd.DataFrame(columns=cols)

        lap_n = int(lap_n)
        safety_car_laps = self._safety_car_laps(lap_n)

        rows = []
        for driver, driver_laps in self.laps.groupby("driver_code"):
            # Skip drivers who have not started by lap_n.
            if (driver_laps["LapNumber"] <= lap_n).sum() == 0:
                continue
            feats = self._driver_features(driver_laps, lap_n)
            feats["driver_code"] = driver
            feats["safety_car_laps"] = safety_car_laps
            feats["is_street_circuit"] = 1.0 if self.is_street_circuit else 0.0
            rows.append(feats)

        if not rows:
            cols = ["driver_code"] + FEATURE_COLUMNS + [f"{c}_missing" for c in FEATURE_COLUMNS]
            return pd.DataFrame(columns=cols)

        df = pd.DataFrame(rows)

        # Add missing indicators and fill NaNs with neutral defaults.
        for col in FEATURE_COLUMNS:
            if col not in df.columns:
                df[col] = np.nan
            df[f"{col}_missing"] = df[col].isna().astype(float)
            df[col] = df[col].fillna(_FILL_DEFAULTS.get(col, 0.0))

        ordered = ["driver_code"] + FEATURE_COLUMNS + [f"{c}_missing" for c in FEATURE_COLUMNS]
        return df[ordered].reset_index(drop=True)
