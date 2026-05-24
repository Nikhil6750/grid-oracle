import json
import time
import pandas as pd
import fastf1
from datetime import datetime
from typing import List, Optional, Dict, Any

from src.data_ingestion.base_ingestor import BaseIngestor
from src.utils.logger import get_logger
from src.utils.paths import PROCESSED_DATA_DIR

logger = get_logger(__name__)

class HistoricalIngestor(BaseIngestor):
    """Ingestor for processing historical F1 data by season and saving as Parquet."""
    
    def __init__(self, force_overwrite: bool = False, dry_run: bool = False, limit_events: int = None):
        super().__init__()
        self.force_overwrite = force_overwrite
        self.dry_run = dry_run
        self.limit_events = limit_events
        self.status_file = PROCESSED_DATA_DIR / "ingestion_metadata" / "ingestion_status.parquet"
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_df = self._load_status()
        self.attempted_seasons = set()
        self.attempted_events = set()
        self.summary = {
            "sessions_attempted": 0,
            "successful_sessions": 0,
            "failed_sessions": 0,
            "skipped_sessions": 0,
            "total_lap_rows": 0,
            "total_result_rows": 0
        }

    def _load_status(self) -> pd.DataFrame:
        if self.status_file.exists():
            return pd.read_parquet(self.status_file)
        return pd.DataFrame(columns=[
            "season", "round", "event_name", "session_type", "status", 
            "error_message", "laps_rows", "results_rows", "weather_rows", 
            "started_at", "finished_at", "duration_seconds", "output_path"
        ])

    def _save_status(self) -> None:
        self.status_df.to_parquet(self.status_file)

    def _get_output_dir(self, year: int, round_number: int) -> pd.DataFrame:
        # Padded round number
        round_str = f"{round_number:02d}"
        output_dir = PROCESSED_DATA_DIR / "sessions" / f"season={year}" / f"round={round_str}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def should_skip_existing(self, year: int, round_number: int, session_type: str) -> bool:
        if self.force_overwrite:
            return False
            
        # Check if it was successfully ingested before
        if not self.status_df.empty:
            match = self.status_df[
                (self.status_df["season"] == year) &
                (self.status_df["round"] == round_number) &
                (self.status_df["session_type"] == session_type) &
                (self.status_df["status"] == "success")
            ]
            if not match.empty:
                return True
        return False

    def update_ingestion_status(self, record: dict) -> None:
        # Convert dictionary to DataFrame row
        new_row = pd.DataFrame([record])
        
        # Ensure it has all required columns
        for col in ["season", "round", "event_name", "session_type", "status", 
                    "error_message", "laps_rows", "results_rows", "weather_rows", 
                    "started_at", "finished_at", "duration_seconds", "output_path"]:
            if col not in new_row.columns:
                new_row[col] = None

        # Drop previous record if exists
        if not self.status_df.empty:
            self.status_df = self.status_df[
                ~((self.status_df["season"] == record.get("season")) &
                  (self.status_df["round"] == record.get("round")) &
                  (self.status_df["session_type"] == record.get("session_type")))
            ]
        
        # Append and save
        if self.status_df.empty:
            self.status_df = new_row.copy()
        else:
            new_row_cleaned = new_row.dropna(axis=1, how='all')
            self.status_df = pd.concat([self.status_df, new_row_cleaned], ignore_index=True)
        self._save_status()

    def save_session_laps(self, session: fastf1.core.Session, out_path: str) -> int:
        if session.laps is not None and not session.laps.empty:
            # Need to convert Timedelta columns to string or float to save as parquet safely
            df = session.laps.copy()
            for col in df.select_dtypes(include=['timedelta64[ns]']).columns:
                df[col] = df[col].dt.total_seconds()
            df.to_parquet(out_path)
            return len(df)
        return 0

    def save_session_results(self, session: fastf1.core.Session, out_path: str) -> int:
        if session.results is not None and not session.results.empty:
            df = session.results.copy()
            for col in df.select_dtypes(include=['timedelta64[ns]']).columns:
                df[col] = df[col].dt.total_seconds()
            df.to_parquet(out_path)
            return len(df)
        return 0

    def save_session_weather(self, session: fastf1.core.Session, out_path: str) -> int:
        if session.weather_data is not None and not session.weather_data.empty:
            df = session.weather_data.copy()
            for col in df.select_dtypes(include=['timedelta64[ns]']).columns:
                df[col] = df[col].dt.total_seconds()
            df.to_parquet(out_path)
            return len(df)
        return 0

    def save_session_metadata(self, session: fastf1.core.Session, out_path: str) -> None:
        metadata = {
            "event_name": session.event.EventName,
            "session_name": session.name,
            "session_date": str(session.date),
            "event_date": str(session.event.EventDate),
            "official_event_format": getattr(session.event, "EventFormat", "conventional"),
        }
        with open(out_path, "w") as f:
            json.dump(metadata, f, indent=4)

    def save_driver_summary(self, session: fastf1.core.Session, out_path: str) -> int:
        # Create a simple summary from laps if available
        if session.laps is not None and not session.laps.empty:
            df = session.laps.copy()
            for col in df.select_dtypes(include=['timedelta64[ns]']).columns:
                df[col] = df[col].dt.total_seconds()
                
            summary = df.groupby('Driver').agg(
                total_laps=('LapNumber', 'count'),
                fastest_lap=('LapTime', 'min'),
                median_lap=('LapTime', 'median')
            ).reset_index()
            summary.to_parquet(out_path)
            return len(summary)
        return 0

    def save_event_manifest(self, year: int, round_number: int, event_info: pd.Series, output_dir) -> None:
        manifest = {
            "season": year,
            "round": round_number,
            "event_name": event_info.get("EventName", "Unknown"),
            "event_date": str(event_info.get("EventDate", "")),
            "country": event_info.get("Country", ""),
            "location": event_info.get("Location", ""),
            "event_format": event_info.get("EventFormat", ""),
        }
        with open(output_dir / "event_manifest.json", "w") as f:
            json.dump(manifest, f, indent=4)

    def ingest_session(self, year: int, round_number: int, session_type: str, event_name: str) -> None:
        self.attempted_seasons.add(year)
        self.attempted_events.add((year, round_number))
        self.summary["sessions_attempted"] += 1
        
        record = {
            "season": year,
            "round": round_number,
            "event_name": event_name,
            "session_type": session_type,
            "started_at": datetime.now().isoformat()
        }
        
        if self.should_skip_existing(year, round_number, session_type):
            logger.info(f"Skipping existing session: {year} Round {round_number} {session_type}")
            record["status"] = "skipped_existing"
            record["finished_at"] = datetime.now().isoformat()
            if not self.dry_run:
                self.update_ingestion_status(record)
            self.summary["skipped_sessions"] += 1
            return
            
        logger.info(f"Ingesting session: {year} Round {round_number} {session_type}")
        if self.dry_run:
            logger.info(f"[DRY RUN] Would ingest: {year} Round {round_number} {session_type}")
            self.summary["successful_sessions"] += 1
            return

        start_time = time.time()
        
        try:
            # First check if available without throwing big error
            if not self.session_available(year, round_number, session_type):
                record["status"] = "missing_session"
                record["error_message"] = "Session not available"
                record["finished_at"] = datetime.now().isoformat()
                if not self.dry_run:
                    self.update_ingestion_status(record)
                self.summary["skipped_sessions"] += 1
                return

            session = self.load_session(year, round_number, session_type)
            
            output_dir = self._get_output_dir(year, round_number)
            
            prefix = f"{session_type}_"
            
            # Save artifacts
            laps_saved = self.save_session_laps(session, str(output_dir / f"{prefix}laps.parquet"))
            results_saved = self.save_session_results(session, str(output_dir / f"{prefix}results.parquet"))
            weather_saved = self.save_session_weather(session, str(output_dir / f"{prefix}weather.parquet"))
            self.save_driver_summary(session, str(output_dir / f"{prefix}driver_summary.parquet"))
            self.save_session_metadata(session, str(output_dir / f"{prefix}session_metadata.json"))
            
            if laps_saved == 0 and results_saved == 0:
                record["status"] = "data_empty"
                self.summary["failed_sessions"] += 1
            else:
                record["status"] = "success"
                self.summary["successful_sessions"] += 1
                
            record["laps_rows"] = laps_saved
            record["results_rows"] = results_saved
            record["weather_rows"] = weather_saved
            record["output_path"] = str(output_dir)
            
            self.summary["total_lap_rows"] += laps_saved
            self.summary["total_result_rows"] += results_saved
            
        except fastf1.core.DataNotLoadedError as e:
            record["status"] = "fastf1_error"
            record["error_message"] = str(e)
            self.summary["failed_sessions"] += 1
        except Exception as e:
            record["status"] = "unknown_error"
            record["error_message"] = str(e)
            self.summary["failed_sessions"] += 1
            logger.error(f"Error ingesting session {year} R{round_number} {session_type}: {e}")
            
        end_time = time.time()
        record["finished_at"] = datetime.now().isoformat()
        record["duration_seconds"] = round(end_time - start_time, 2)
        
        self.update_ingestion_status(record)

    def ingest_event(self, year: int, round_number: int, sessions_to_fetch: List[str] = None) -> None:
        try:
            schedule = self.get_event_schedule(year)
            # Find the specific event
            event_row = schedule[schedule['RoundNumber'] == round_number]
            if event_row.empty:
                logger.error(f"Round {round_number} not found for year {year}")
                return
                
            event_info = event_row.iloc[0]
            event_name = event_info['EventName']
            
            output_dir = self._get_output_dir(year, round_number)
            self.save_event_manifest(year, round_number, event_info, output_dir)
            
            # Default sessions to attempt if not specified
            if not sessions_to_fetch:
                sessions_to_fetch = ['FP1', 'FP2', 'FP3', 'SQ', 'S', 'Q', 'R']
                
            for session_type in sessions_to_fetch:
                self.ingest_session(year, round_number, session_type, event_name)
                
        except Exception as e:
            logger.error(f"Failed to ingest event {year} R{round_number}: {e}")

    def ingest_season(self, year: int, sessions_to_fetch: List[str] = None) -> None:
        try:
            schedule = self.get_event_schedule(year)
            
            # Save schedule
            schedules_dir = PROCESSED_DATA_DIR / "schedules"
            schedules_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert datetime columns before saving to parquet
            df_sched = schedule.copy()
            for col in df_sched.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns:
                df_sched[col] = df_sched[col].dt.strftime('%Y-%m-%dT%H:%M:%S')
            df_sched.to_parquet(schedules_dir / f"schedule_{year}.parquet")
            
            rounds = df_sched[df_sched['RoundNumber'] > 0]['RoundNumber'].tolist()
            if self.limit_events:
                rounds = rounds[:self.limit_events]
            
            for round_num in rounds:
                self.ingest_event(year, round_num, sessions_to_fetch)
                
        except Exception as e:
            logger.error(f"Failed to ingest season {year}: {e}")

    def ingest_season_range(self, start_year: int, end_year: int, sessions_to_fetch: List[str] = None) -> None:
        for year in range(start_year, end_year + 1):
            self.ingest_season(year, sessions_to_fetch)

    def get_ingestion_summary(self) -> dict:
        summary_copy = self.summary.copy()
        summary_copy["seasons_attempted"] = len(self.attempted_seasons)
        summary_copy["events_attempted"] = len(self.attempted_events)
        # Reorder to keep seasons and events at the top
        return {
            "seasons_attempted": summary_copy["seasons_attempted"],
            "events_attempted": summary_copy["events_attempted"],
            **self.summary
        }
