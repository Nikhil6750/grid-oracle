import pytest
import pandas as pd
from pathlib import Path

from scripts.audit_ingestion import audit, load_status


def make_status_df(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal ingestion_status DataFrame from a list of row dicts."""
    defaults = {
        "season": 2023, "round": 1, "event_name": "Test GP",
        "session_type": "R", "status": "success",
        "error_message": None, "laps_rows": 100, "results_rows": 20,
        "weather_rows": 50, "started_at": "2023-01-01T00:00:00",
        "finished_at": "2023-01-01T00:01:00", "duration_seconds": 60.0,
        "output_path": "/some/path"
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


# --- load_status tests ---

def test_load_status_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "does_not_exist.parquet"
    df = load_status(missing)
    assert df.empty


def test_load_status_reads_parquet(tmp_path):
    path = tmp_path / "ingestion_status.parquet"
    expected = make_status_df([{"season": 2022, "session_type": "Q", "status": "success"}])
    expected.to_parquet(path)
    result = load_status(path)
    assert len(result) == 1
    assert result.iloc[0]["season"] == 2022


# --- audit filter tests ---

def test_audit_filters_by_season(capsys):
    df = make_status_df([
        {"season": 2021, "session_type": "Q"},
        {"season": 2022, "session_type": "Q"},
    ])
    audit(df, season=2021)
    captured = capsys.readouterr()
    assert "2021" in captured.out
    assert "2022" not in captured.out


def test_audit_filters_by_status(capsys):
    df = make_status_df([
        {"season": 2023, "session_type": "Q", "status": "success"},
        {"season": 2023, "session_type": "R", "status": "fastf1_error", "error_message": "boom"},
    ])
    audit(df, status_filter="fastf1_error")
    captured = capsys.readouterr()
    assert "fastf1_error" in captured.out


def test_audit_filters_by_sessions(capsys):
    df = make_status_df([
        {"session_type": "Q", "status": "success"},
        {"session_type": "FP1", "status": "success"},
    ])
    audit(df, sessions_filter=["Q"])
    captured = capsys.readouterr()
    assert "Q" in captured.out
    assert "FP1" not in captured.out


def test_audit_identifies_failed_sessions(capsys):
    df = make_status_df([
        {"session_type": "R", "status": "fastf1_error", "error_message": "Rate limit hit"},
    ])
    audit(df)
    captured = capsys.readouterr()
    assert "Rate limit hit" in captured.out


def test_audit_identifies_incomplete_qr_coverage(capsys):
    df = make_status_df([
        {"season": 2023, "round": 1, "session_type": "Q", "status": "success"},
        # R is missing for round 1 — coverage is incomplete
        {"season": 2023, "round": 2, "session_type": "Q", "status": "success"},
        {"season": 2023, "round": 2, "session_type": "R", "status": "success"},
    ])
    audit(df)
    captured = capsys.readouterr()
    # Round 1 should be flagged as missing R
    assert "R01" in captured.out or "Round 1" in captured.out or "missing: R" in captured.out
    # Year 2023 round 2 should be complete
    assert "✅ Full Q/R coverage" not in captured.out  # not full because round 1 is missing


def test_audit_full_qr_coverage(capsys):
    df = make_status_df([
        {"season": 2023, "round": 1, "session_type": "Q", "status": "success"},
        {"season": 2023, "round": 1, "session_type": "R", "status": "success"},
    ])
    audit(df)
    captured = capsys.readouterr()
    assert "✅ Full Q/R coverage" in captured.out
