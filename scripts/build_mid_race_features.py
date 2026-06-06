"""
Build the mid-race training dataset.

Walks every race (2018-2026) that has lap data, snapshots per-driver features at a
set of lap milestones using :class:`MidRaceFeatureBuilder`, and attaches the true
final finishing position from ``R_results.parquet`` as the target.

Output: ``data/features/mid_race_features.parquet`` with columns::

    season, round, lap_n, pct_complete, driver_code,
    <all mid-race features + *_missing indicators>,
    target_final_position

LeakageGuard: features come solely from laps <= lap_n; the final position is only
ever attached as ``target_final_position`` (never as an input feature).

Run:
    python scripts/build_mid_race_features.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.feature_engineering.mid_race_features import (  # noqa: E402
    MidRaceFeatureBuilder,
    STREET_CIRCUIT_KEYWORDS,
)

SESSIONS_DIR = ROOT_DIR / "data" / "processed" / "sessions"
OUTPUT_PATH = ROOT_DIR / "data" / "features" / "mid_race_features.parquet"

# Lap milestones at which to snapshot the race. ``final-5`` is added per race.
BASE_LAP_INTERVALS = [10, 20, 30, 40, 50]


def _read_event_name(race_dir: Path) -> str | None:
    """Read the event name from session metadata / manifest if available."""
    for fname in ("R_session_metadata.json", "event_manifest.json"):
        fpath = race_dir / fname
        if fpath.exists():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    return json.load(f).get("event_name")
            except Exception:
                continue
    return None


def _load_final_positions(race_dir: Path) -> dict[str, float]:
    """Map driver_code -> final finishing position from R_results.parquet."""
    res_path = race_dir / "R_results.parquet"
    if not res_path.exists():
        return {}
    try:
        res = pd.read_parquet(res_path)
    except Exception:
        return {}
    if res.empty or "Abbreviation" not in res.columns or "Position" not in res.columns:
        return {}
    res = res[res["Position"].notna()]
    return {
        str(code): float(pos)
        for code, pos in zip(res["Abbreviation"], res["Position"])
    }


def _lap_milestones(total_laps: int) -> list[int]:
    """Lap snapshots for a race: fixed intervals plus ``final-5``, clamped."""
    if total_laps <= 0:
        return []
    laps = {n for n in BASE_LAP_INTERVALS if n < total_laps}
    final_minus_5 = max(total_laps - 5, 1)
    laps.add(final_minus_5)
    return sorted(laps)


def build_race(season: int, round_num: int, race_dir: Path) -> pd.DataFrame:
    """Build all milestone snapshots for a single race."""
    laps_path = race_dir / "R_laps.parquet"
    if not laps_path.exists():
        return pd.DataFrame()

    try:
        laps = pd.read_parquet(laps_path)
    except Exception as e:
        print(f"  [SKIP] {season} R{round_num}: failed to read laps ({e})")
        return pd.DataFrame()

    if laps.empty or "LapNumber" not in laps.columns:
        return pd.DataFrame()

    final_positions = _load_final_positions(race_dir)
    if not final_positions:
        print(f"  [SKIP] {season} R{round_num}: no final results")
        return pd.DataFrame()

    event_name = _read_event_name(race_dir)
    is_street = bool(
        event_name and any(kw in event_name.lower() for kw in STREET_CIRCUIT_KEYWORDS)
    )

    builder = MidRaceFeatureBuilder(
        laps, is_street_circuit=is_street, event_name=event_name
    )
    total_laps = builder.total_laps
    milestones = _lap_milestones(total_laps)
    if not milestones:
        return pd.DataFrame()

    frames = []
    for lap_n in milestones:
        feats = builder.build_features_at_lap(lap_n)
        if feats.empty:
            continue
        feats.insert(0, "season", season)
        feats.insert(1, "round", round_num)
        feats.insert(2, "lap_n", lap_n)
        feats.insert(3, "pct_complete", lap_n / total_laps if total_laps else 0.0)
        feats["target_final_position"] = feats["driver_code"].map(final_positions)
        # Keep only drivers we have a final position for.
        feats = feats[feats["target_final_position"].notna()]
        if not feats.empty:
            frames.append(feats)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    if not SESSIONS_DIR.exists():
        raise SystemExit(f"Sessions directory not found: {SESSIONS_DIR}")

    all_frames = []
    races_built = 0

    for season_dir in sorted(SESSIONS_DIR.glob("season=*")):
        try:
            season = int(season_dir.name.split("=")[1])
        except (IndexError, ValueError):
            continue
        if not (2018 <= season <= 2026):
            continue

        for round_dir in sorted(season_dir.glob("round=*")):
            try:
                round_num = int(round_dir.name.split("=")[1])
            except (IndexError, ValueError):
                continue

            race_df = build_race(season, round_num, round_dir)
            if not race_df.empty:
                all_frames.append(race_df)
                races_built += 1
                print(
                    f"  [OK] {season} R{round_num:02d}: "
                    f"{len(race_df)} rows, {race_df['lap_n'].nunique()} snapshots"
                )

    if not all_frames:
        raise SystemExit("No mid-race features were built. Check lap/result data.")

    dataset = pd.concat(all_frames, ignore_index=True)
    # Reorder so identifiers/target sit at the edges and features in the middle.
    id_cols = ["season", "round", "lap_n", "pct_complete", "driver_code"]
    target_col = "target_final_position"
    feature_cols = [c for c in dataset.columns if c not in id_cols + [target_col]]
    dataset = dataset[id_cols + feature_cols + [target_col]]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_parquet(OUTPUT_PATH, index=False)

    print("\n" + "=" * 60)
    print(f"Built mid-race features for {races_built} races.")
    print(f"Total rows:    {len(dataset)}")
    print(f"Seasons:       {sorted(dataset['season'].unique().tolist())}")
    print(f"Columns:       {len(dataset.columns)}")
    print(f"Saved to:      {OUTPUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
