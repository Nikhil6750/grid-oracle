import pytest
from pathlib import Path
import pandas as pd
import json

from src.data_ingestion.historical_ingestor import HistoricalIngestor

def test_metadata_tracking(tmp_path, monkeypatch):
    monkeypatch.setattr("src.data_ingestion.historical_ingestor.PROCESSED_DATA_DIR", tmp_path)
    
    ingestor = HistoricalIngestor()
    
    # Test initial state
    assert ingestor.status_df.empty
    
    # Test adding a record
    record = {
        "season": 2023,
        "round": 1,
        "event_name": "Bahrain Grand Prix",
        "session_type": "R",
        "status": "success",
        "laps_rows": 1000
    }
    ingestor.update_ingestion_status(record)
    
    assert not ingestor.status_df.empty
    assert len(ingestor.status_df) == 1
    assert ingestor.status_df.iloc[0]["season"] == 2023
    assert ingestor.status_df.iloc[0]["status"] == "success"
    
    # Check if parquet file was saved
    assert (tmp_path / "ingestion_metadata" / "ingestion_status.parquet").exists()
    
    # Test updating same record overwrites, doesn't duplicate
    record2 = {
        "season": 2023,
        "round": 1,
        "event_name": "Bahrain Grand Prix",
        "session_type": "R",
        "status": "data_empty",
        "laps_rows": 0
    }
    ingestor.update_ingestion_status(record2)
    assert len(ingestor.status_df) == 1
    assert ingestor.status_df.iloc[0]["status"] == "data_empty"

def test_skip_existing_behavior(tmp_path, monkeypatch):
    monkeypatch.setattr("src.data_ingestion.historical_ingestor.PROCESSED_DATA_DIR", tmp_path)
    
    ingestor = HistoricalIngestor()
    
    # Add a successful record
    record = {
        "season": 2023,
        "round": 1,
        "event_name": "Bahrain Grand Prix",
        "session_type": "R",
        "status": "success"
    }
    ingestor.update_ingestion_status(record)
    
    # Should skip
    assert ingestor.should_skip_existing(2023, 1, "R") is True
    
    # Should not skip missing session
    assert ingestor.should_skip_existing(2023, 1, "Q") is False

def test_force_overwrite_behavior(tmp_path, monkeypatch):
    monkeypatch.setattr("src.data_ingestion.historical_ingestor.PROCESSED_DATA_DIR", tmp_path)
    
    ingestor = HistoricalIngestor(force_overwrite=True)
    
    # Add a successful record
    record = {
        "season": 2023,
        "round": 1,
        "event_name": "Bahrain Grand Prix",
        "session_type": "R",
        "status": "success"
    }
    ingestor.update_ingestion_status(record)
    
    # Should NOT skip because force_overwrite=True
    assert ingestor.should_skip_existing(2023, 1, "R") is False

def test_event_manifest_writing(tmp_path, monkeypatch):
    monkeypatch.setattr("src.data_ingestion.historical_ingestor.PROCESSED_DATA_DIR", tmp_path)
    
    ingestor = HistoricalIngestor()
    
    # Mock event info
    event_info = pd.Series({
        "EventName": "Bahrain Grand Prix",
        "EventDate": "2023-03-05",
        "Country": "Bahrain",
        "Location": "Sakhir",
        "EventFormat": "conventional"
    })
    
    output_dir = tmp_path / "sessions" / "season=2023" / "round=01"
    output_dir.mkdir(parents=True)
    
    ingestor.save_event_manifest(2023, 1, event_info, output_dir)
    
    manifest_path = output_dir / "event_manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r") as f:
        data = json.load(f)
        
    assert data["season"] == 2023
    assert data["event_name"] == "Bahrain Grand Prix"

def test_ingestion_summary_counting(tmp_path, monkeypatch):
    monkeypatch.setattr("src.data_ingestion.historical_ingestor.PROCESSED_DATA_DIR", tmp_path)
    ingestor = HistoricalIngestor()
    
    # Mock some methods to prevent actual FastF1 calls
    def mock_should_skip(year, round_num, session_type):
        return False
    
    def mock_session_available(year, round_num, session_type):
        return False
    
    monkeypatch.setattr(ingestor, "should_skip_existing", mock_should_skip)
    monkeypatch.setattr(ingestor, "session_available", mock_session_available)
    
    # Attempt 2 sessions for 1 event
    ingestor.ingest_session(2023, 1, "Q", "Event")
    ingestor.ingest_session(2023, 1, "R", "Event")
    
    summary = ingestor.get_ingestion_summary()
    assert summary["seasons_attempted"] == 1
    assert summary["events_attempted"] == 1
    assert summary["sessions_attempted"] == 2
    
    # Attempt another event in the same season
    ingestor.ingest_session(2023, 2, "Q", "Event")
    
    summary = ingestor.get_ingestion_summary()
    assert summary["seasons_attempted"] == 1
    assert summary["events_attempted"] == 2
    assert summary["sessions_attempted"] == 3
    
    # Attempt another season
    ingestor.ingest_session(2024, 1, "R", "Event")
    
    summary = ingestor.get_ingestion_summary()
    assert summary["seasons_attempted"] == 2
    assert summary["events_attempted"] == 3
    assert summary["sessions_attempted"] == 4

def test_update_ingestion_status_pandas_warning(tmp_path, monkeypatch):
    monkeypatch.setattr("src.data_ingestion.historical_ingestor.PROCESSED_DATA_DIR", tmp_path)
    ingestor = HistoricalIngestor()
    
    record = {
        "season": 2023,
        "round": 1,
        "event_name": "Bahrain Grand Prix",
        "session_type": "R",
        "status": "success",
        "laps_rows": 1000
    }
    
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        ingestor.update_ingestion_status(record)
        
        # Check that no FutureWarning was raised from pandas concat
        for warning in w:
            assert not (issubclass(warning.category, FutureWarning) and "concat" in str(warning.message).lower())
            
    # And again to verify it works when not empty
    record2 = {
        "season": 2023,
        "round": 1,
        "event_name": "Bahrain Grand Prix",
        "session_type": "Q",
        "status": "success",
        "laps_rows": 1000
    }
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        ingestor.update_ingestion_status(record2)
        
        for warning in w:
            assert not (issubclass(warning.category, FutureWarning) and "concat" in str(warning.message).lower())
