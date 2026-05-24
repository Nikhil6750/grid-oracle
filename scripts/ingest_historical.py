import argparse
import sys
from pathlib import Path
from datetime import datetime
import json

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.data_ingestion.historical_ingestor import HistoricalIngestor
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Historical F1 Data Ingestion")
    parser.add_argument("--latest", action="store_true", help="Ingest the latest available season")
    parser.add_argument("--sessions", nargs="+", choices=["FP1", "FP2", "FP3", "Q", "SQ", "S", "R"], help="Specific sessions to fetch")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing sessions")
    parser.add_argument("--season", type=int, help="Specific season year to ingest")
    parser.add_argument("--round", type=int, help="Specific round number to ingest")
    parser.add_argument("--start-year", type=int, help="Start year for ingestion range")
    parser.add_argument("--end-year", type=int, help="End year for ingestion range")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be ingested without downloading")
    parser.add_argument("--limit-events", type=int, help="Limit the number of events per season (for smoke testing)")

    args = parser.parse_args()
    
    ingestor = HistoricalIngestor(
        force_overwrite=args.force, 
        dry_run=args.dry_run, 
        limit_events=args.limit_events
    )
    
    if args.latest:
        year = datetime.now().year
        logger.info(f"Ingesting latest season: {year}")
        ingestor.ingest_season(year, args.sessions)
    elif args.start_year and args.end_year:
        logger.info(f"Ingesting seasons from {args.start_year} to {args.end_year}")
        ingestor.ingest_season_range(args.start_year, args.end_year, args.sessions)
    elif args.season and args.round:
        logger.info(f"Ingesting season {args.season} round {args.round}")
        ingestor.ingest_event(args.season, args.round, args.sessions)
    elif args.season:
        logger.info(f"Ingesting season {args.season}")
        ingestor.ingest_season(args.season, args.sessions)
    else:
        logger.error("Must provide --latest, --start-year/--end-year, --season, or --season/--round")
        sys.exit(1)
        
    summary = ingestor.get_ingestion_summary()
    logger.info("=== Ingestion Summary ===")
    print(json.dumps(summary, indent=4))
    for k, v in summary.items():
        logger.info(f"{k}: {v}")

if __name__ == "__main__":
    main()
