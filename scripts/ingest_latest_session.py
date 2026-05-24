"""
Auto-ingests the most recent completed session for a given race round.
Detects which sessions are available (Q, SQ, S, R) and ingests only new ones.
Designed to be run after each session ends — e.g. via task scheduler or cron.

Usage:
    python scripts/ingest_latest_session.py --season 2026 --round 5
    python scripts/ingest_latest_session.py --season 2026 --round 5 --session Q
    python scripts/ingest_latest_session.py --auto   # scans for the current active round
"""
import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
import os; os.chdir(ROOT_DIR)

import fastf1
import datetime
from src.data_ingestion.historical_ingestor import HistoricalIngestor

SESSION_SEQUENCE = ['SQ', 'S', 'Q', 'R']  # Sprint Qualifying, Sprint, Qualifying, Race

def ingest_session(season: int, round_num: int, session_type: str, force: bool = False):
    print(f"[{season} R{round_num}] Ingesting session: {session_type}")
    ingestor = HistoricalIngestor(force_overwrite=force)
    try:
        ingestor.ingest_event(season, round_num, [session_type])
        print(f"[{season} R{round_num}] Session {session_type} ingestion complete.")
    except Exception as e:
        print(f"[WARN] Failed to ingest {session_type}: {e}")

def find_current_active_round(season: int) -> int:
    schedule = fastf1.get_event_schedule(season)
    now = datetime.datetime.now()
    
    # Filter to future/current races
    # EventDate is the end of the weekend
    upcoming = schedule[schedule['EventDate'] >= pd.Timestamp(now)]
    if not upcoming.empty:
        return upcoming.iloc[0]['RoundNumber']
        
    # If all finished, return last round
    return schedule['RoundNumber'].max()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', type=int, default=datetime.datetime.now().year)
    parser.add_argument('--round', type=int)
    parser.add_argument('--session', type=str, choices=SESSION_SEQUENCE)
    parser.add_argument('--auto', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    
    import pandas as pd
    
    season = args.season
    if args.auto or not args.round:
        round_num = find_current_active_round(season)
        print(f"Auto-detected active round: {season} R{round_num}")
    else:
        round_num = args.round
        
    if args.session:
        ingest_session(season, round_num, args.session, args.force)
    else:
        for s in SESSION_SEQUENCE:
            # Check if it already exists to avoid redundant ingestion unless forced
            parquet_path = ROOT_DIR / f"data/processed/sessions/season={season}/round={round_num:02d}/{s}_results.parquet"
            if not parquet_path.exists() or args.force:
                ingest_session(season, round_num, s, args.force)
            else:
                print(f"[{season} R{round_num}] Session {s} already exists, skipping.")
