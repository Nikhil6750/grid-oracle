import pytest
from pathlib import Path
from src.config.settings import settings
from src.utils.paths import ROOT_DIR, DATA_DIR, FASTF1_CACHE_DIR, create_directories
from src.data_ingestion.base_ingestor import BaseIngestor

def test_settings_load():
    """Test that pydantic settings load correctly."""
    assert settings.pitwall_env in ["development", "production", "testing"]
    assert hasattr(settings, "log_level")

def test_paths_resolve():
    """Test that paths resolve to valid Path objects."""
    assert isinstance(ROOT_DIR, Path)
    assert isinstance(DATA_DIR, Path)
    assert isinstance(FASTF1_CACHE_DIR, Path)

def test_directory_creation(tmp_path, monkeypatch):
    """Test that directories are created properly."""
    # Monkeypatch ROOT_DIR to a temp path to avoid polluting the actual project
    monkeypatch.setattr("src.utils.paths.ROOT_DIR", tmp_path)
    monkeypatch.setattr("src.utils.paths.DATA_DIR", tmp_path / "data")
    monkeypatch.setattr("src.utils.paths.FASTF1_CACHE_DIR", tmp_path / "data" / "raw" / "fastf1_cache")
    monkeypatch.setattr("src.utils.paths.LOGS_DIR", tmp_path / "logs")
    
    from src.utils.paths import DATA_DIR, FASTF1_CACHE_DIR, LOGS_DIR
    
    # Create the dirs
    from src.utils.paths import create_directories as mocked_create_directories
    mocked_create_directories()
    
    # Re-import to get the monkeypatched ones inside the function scope if necessary
    import src.utils.paths as patched_paths
    
    assert patched_paths.DATA_DIR.exists()
    assert patched_paths.FASTF1_CACHE_DIR.exists()
    assert patched_paths.LOGS_DIR.exists()

def test_base_ingestor_init(tmp_path, monkeypatch):
    """Test that base ingestor initializes and enables cache."""
    # Prevent creating the actual cache dir by monkeypatching
    cache_path = tmp_path / "cache"
    monkeypatch.setattr("src.utils.paths.FASTF1_CACHE_DIR", cache_path)
    monkeypatch.setattr("src.data_ingestion.base_ingestor.FASTF1_CACHE_DIR", cache_path)
    
    # Initialize ingestor
    ingestor = BaseIngestor()
    
    # Assert cache directory was created
    assert cache_path.exists()
