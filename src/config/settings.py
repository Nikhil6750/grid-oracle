from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    pitwall_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    
    # Path settings. Since paths.py handles resolution, we can just store the relative paths here or rely on paths.py.
    # To keep it cohesive with pydantic, let's allow overriding.
    fastf1_cache_dir: str = Field(default="data/raw/fastf1_cache")
    data_dir: str = Field(default="data")
    raw_data_dir: str = Field(default="data/raw")
    processed_data_dir: str = Field(default="data/processed")
    features_data_dir: str = Field(default="data/features")
    external_data_dir: str = Field(default="data/external")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
