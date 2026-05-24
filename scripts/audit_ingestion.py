"""
audit_ingestion.py — PitWall AI ingestion status auditor.

Usage:
  python scripts/audit_ingestion.py
  python scripts/audit_ingestion.py --season 2023
  python scripts/audit_ingestion.py --status failed
  python scripts/audit_ingestion.py --sessions Q R
"""

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import pandas as pd

from src.utils.paths import PROCESSED_DATA_DIR


STATUS_FILE = PROCESSED_DATA_DIR / "ingestion_metadata" / "ingestion_status.parquet"
SESSIONS_DIR = PROCESSED_DATA_DIR / "sessions"


def get_dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return round(total / (1024 * 1024), 2)


def load_status(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[WARNING] ingestion_status.parquet not found at {path}")
        return pd.DataFrame()
    return pd.read_parquet(path)


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def audit(df: pd.DataFrame, season: int = None, status_filter: str = None, sessions_filter: list = None):
    # Apply filters
    if season is not None:
        df = df[df["season"] == season]
    if status_filter is not None:
        df = df[df["status"] == status_filter]
    if sessions_filter:
        df = df[df["session_type"].isin(sessions_filter)]

    if df.empty:
        print("\n[INFO] No rows matched the given filters.")
        return

    print_section("OVERVIEW")
    print(f"  Total rows in ingestion status : {len(df)}")
    
    print_section("ROWS BY SEASON")
    season_counts = df.groupby("season").size().reset_index(name="count")
    print(season_counts.to_string(index=False))

    print_section("ROWS BY SESSION TYPE")
    session_counts = df.groupby("session_type").size().reset_index(name="count")
    print(session_counts.to_string(index=False))

    print_section("ROWS BY STATUS")
    status_counts = df.groupby("status").size().reset_index(name="count")
    print(status_counts.to_string(index=False))

    print_section("SUCCESSFUL SESSIONS BY SEASON")
    success_df = df[df["status"] == "success"]
    if not success_df.empty:
        success_by_season = success_df.groupby("season").size().reset_index(name="count")
        print(success_by_season.to_string(index=False))
        print(f"\n  Total successful: {len(success_df)}")
    else:
        print("  None.")

    print_section("FAILED SESSIONS (with error messages)")
    failed_df = df[df["status"].isin(["fastf1_error", "unknown_error", "data_empty", "save_error"])]
    if not failed_df.empty:
        cols = ["season", "round", "event_name", "session_type", "status", "error_message"]
        available = [c for c in cols if c in failed_df.columns]
        print(failed_df[available].to_string(index=False))
    else:
        print("  No failed sessions.")

    print_section("SKIPPED / MISSING SESSIONS")
    skipped_df = df[df["status"].isin(["skipped_existing", "missing_session", "session_not_yet_available"])]
    if not skipped_df.empty:
        skip_cols = ["season", "round", "event_name", "session_type", "status"]
        available = [c for c in skip_cols if c in skipped_df.columns]
        print(skipped_df[available].to_string(index=False))
        print(f"\n  Total skipped/missing: {len(skipped_df)}")
    else:
        print("  None.")

    print_section("LAP AND RESULT ROW TOTALS")
    total_laps = pd.to_numeric(df.get("laps_rows", pd.Series(dtype=float)), errors="coerce").sum()
    total_results = pd.to_numeric(df.get("results_rows", pd.Series(dtype=float)), errors="coerce").sum()
    print(f"  Total lap rows     : {int(total_laps)}")
    print(f"  Total result rows  : {int(total_results)}")

    print_section("DISK USAGE")
    size_mb = get_dir_size_mb(SESSIONS_DIR)
    status_size = round(STATUS_FILE.stat().st_size / 1024, 2) if STATUS_FILE.exists() else 0
    print(f"  Sessions dir size  : {size_mb} MB")
    print(f"  Status parquet     : {status_size} KB")

    print_section("INCOMPLETE Q/R COVERAGE BY SEASON")
    all_seasons = sorted(df["season"].unique())
    for yr in all_seasons:
        yr_df = df[df["season"] == yr]
        rounds = yr_df["round"].unique()
        incomplete = []
        for rnd in sorted(rounds):
            rnd_df = yr_df[yr_df["round"] == rnd]
            q_ok = any((rnd_df["session_type"] == "Q") & (rnd_df["status"] == "success"))
            r_ok = any((rnd_df["session_type"] == "R") & (rnd_df["status"] == "success"))
            if not q_ok or not r_ok:
                event_name = rnd_df["event_name"].iloc[0] if "event_name" in rnd_df.columns else f"Round {rnd}"
                missing = []
                if not q_ok:
                    missing.append("Q")
                if not r_ok:
                    missing.append("R")
                incomplete.append(f"    R{rnd:02d} {event_name} — missing: {', '.join(missing)}")
        if incomplete:
            print(f"\n  {yr}:")
            for line in incomplete:
                print(line)
        else:
            print(f"\n  {yr}: ✅ Full Q/R coverage")

    print()


def main():
    parser = argparse.ArgumentParser(description="Audit PitWall AI ingestion status")
    parser.add_argument("--season", type=int, help="Filter by season year")
    parser.add_argument("--status", type=str, help="Filter by status (e.g. failed, success, skipped_existing)")
    parser.add_argument("--sessions", nargs="+", help="Filter by session types (e.g. Q R)")
    args = parser.parse_args()

    df = load_status(STATUS_FILE)

    if df.empty:
        print("[ERROR] No ingestion data available to audit.")
        sys.exit(0)

    audit(df, season=args.season, status_filter=args.status, sessions_filter=args.sessions)


if __name__ == "__main__":
    main()
