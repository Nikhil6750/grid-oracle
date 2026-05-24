import json
import pandas as pd
from pathlib import Path
from typing import List, Dict

from src.utils.paths import PROCESSED_DATA_DIR


class DataLoader:
    """Loads historical data from Phase 2 parquet artifacts."""
    
    def __init__(self, data_dir: Path = PROCESSED_DATA_DIR):
        self.data_dir = data_dir
        self.sessions_dir = self.data_dir / "sessions"
        self.metadata_dir = self.data_dir / "ingestion_metadata"
        self.skipped_events: List[Dict] = []
        
    def get_ingestion_status(self) -> pd.DataFrame:
        status_path = self.metadata_dir / "ingestion_status.parquet"
        if status_path.exists():
            return pd.read_parquet(status_path)
        return pd.DataFrame()
        
    def load_session_results(self, session_type_filter: str = None) -> pd.DataFrame:
        """Loads all results.parquet files into a single DataFrame."""
        return self._load_parquet_files("*_results.parquet", session_type_filter)
        
    def load_session_laps(self, session_type_filter: str = None) -> pd.DataFrame:
        """Loads all laps.parquet files into a single DataFrame."""
        return self._load_parquet_files("*_laps.parquet", session_type_filter)
        
    def load_session_weather(self, session_type_filter: str = None) -> pd.DataFrame:
        """Loads all weather.parquet files into a single DataFrame."""
        return self._load_parquet_files("*_weather.parquet", session_type_filter)

    def _load_parquet_files(self, glob_pattern: str, session_type_filter: str = None) -> pd.DataFrame:
        """Helper to load generic parquet files from session folders."""
        result_files = list(self.sessions_dir.rglob(glob_pattern))
        dfs = []
        for f in result_files:
            try:
                # Path format: season=2023/round=01/R_results.parquet
                season = int(f.parent.parent.name.split("=")[1])
                round_num = int(f.parent.name.split("=")[1])
                session_type = f.name.split("_")[0]
                
                if session_type_filter and session_type != session_type_filter:
                    continue
                
                df = pd.read_parquet(f)
                if df.empty:
                    self.skipped_events.append({
                        "season": season,
                        "round": round_num,
                        "session_type": session_type,
                        "reason": f"Empty parquet file: {f.name}",
                    })
                    print(f"[SKIP] Season {season} Round {round_num} {session_type}: empty parquet")
                    continue
                    
                df['season'] = season
                df['round'] = round_num
                df['session_type'] = session_type
                
                # Fetch metadata to get event_name
                metadata_file = f.parent / f"{session_type}_session_metadata.json"
                event_name = f"Round {round_num}"
                if metadata_file.exists():
                    meta = pd.read_json(metadata_file, typ='series')
                    event_name = meta.get('event_name', event_name)
                    
                df['event_name'] = event_name
                
                # Standardize driver identifier columns
                df = df.rename(columns={
                    'DriverNumber': 'driver_number',
                    'Abbreviation': 'driver_code',
                    'Driver': 'driver_code',  # FastF1 uses Driver for laps.parquet
                    'TeamName': 'team',
                    'Team': 'team' # FastF1 uses Team for laps.parquet
                })
                
                # Ensure correct types
                if 'driver_number' in df.columns:
                    df['driver_number'] = df['driver_number'].astype(str)
                if 'driver_code' in df.columns:
                    df['driver_code'] = df['driver_code'].astype(str)
                    df['driver'] = df['driver_code']  # Fallback to driver_code as driver name
                
                dfs.append(df)
            except Exception as e:
                season_str = "?"
                round_str = "?"
                try:
                    season_str = f.parent.parent.name.split("=")[1]
                    round_str = f.parent.name.split("=")[1]
                except Exception:
                    pass
                self.skipped_events.append({
                    "season": season_str,
                    "round": round_str,
                    "session_type": f.name.split("_")[0] if "_" in f.name else "?",
                    "reason": str(e),
                })
                print(f"[SKIP] Failed to load {f}: {e}")
                
        if not dfs:
            return pd.DataFrame()
            
        combined = pd.concat(dfs, ignore_index=True)
        # Sort chronologically
        combined = combined.sort_values(by=['season', 'round']).reset_index(drop=True)
        return combined

    def load_circuit_metadata(self) -> pd.DataFrame:
        """Loads the manually defined circuit metadata."""
        path = Path("data/external/circuit_metadata.csv")
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()
