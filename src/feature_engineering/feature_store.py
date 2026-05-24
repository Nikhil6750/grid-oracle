import json
from pathlib import Path
import pandas as pd
import numpy as np

from src.feature_engineering.data_loader import DataLoader
from src.feature_engineering.driver_features import DriverFeatureBuilder
from src.feature_engineering.team_features import TeamFeatureBuilder
from src.feature_engineering.circuit_features import CircuitFeatureBuilder
from src.feature_engineering.weekend_features import WeekendFeatureBuilder
from src.feature_engineering.target_builder import TargetBuilder
from src.feature_engineering.leakage_validator import LeakageValidator


class FeatureStore:
    """Orchestrates the feature engineering pipeline."""
    
    def __init__(self, out_dir: str = "data/features"):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.loader = DataLoader()
        
    def _ensure_qualifying_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure qualifying columns exist with proper imputation and missing indicators.
        
        For pre_weekend rows, qualifying columns won't exist. We add them with neutral values and missing=1.
        All *_missing columns are guaranteed to contain only 0 or 1 (never null).
        """
        if df.empty:
            return df

        quali_cols = {
            'qualifying_position': 20.0,
            'qualifying_gap_to_pole': 5.0,
            'teammate_qualifying_delta': 0.0,
            'team_qualifying_rank': 10,
            'driver_qualified_ahead_of_teammate': 0,
        }
        
        for col, neutral in quali_cols.items():
            missing_col = f"{col}_missing"
            if col not in df.columns:
                df[col] = neutral
                df[missing_col] = 1
            else:
                if missing_col not in df.columns:
                    df[missing_col] = df[col].isna().astype(int)
                df[col] = df[col].fillna(neutral)
                
            df[missing_col] = df[missing_col].fillna(1).astype(int)
            
        return df

    def _ensure_sprint_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure sprint columns exist with proper imputation and missing indicators.
        
        For non-sprint race rows that go through post_qualifying (not post_sprint),
        sprint columns won't exist. We add them with neutral values and missing=1.
        All *_missing columns are guaranteed to contain only 0 or 1 (never null).
        """
        if df.empty:
            return df

        sprint_cols = {
            'sprint_position': 20.0,
            'sprint_points': 0.0,
            'sprint_finish_status': 'Unknown',
            'sprint_position_gain_loss': 0.0,
        }
        
        for col, neutral in sprint_cols.items():
            missing_col = f"{col}_missing"
            if col not in df.columns:
                df[col] = neutral
                df[missing_col] = 1
            else:
                # Column exists but might have NaN from merge mismatches
                if missing_col not in df.columns:
                    df[missing_col] = df[col].isna().astype(int)
                df[col] = df[col].fillna(neutral)
                
            # Final guarantee: _missing is always 0 or 1, never null
            df[missing_col] = df[missing_col].fillna(1).astype(int)
            
        return df

    def _fix_all_missing_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Guarantee that every *_missing column contains only 0 or 1, never null."""
        if df.empty:
            return df
        missing_cols = [c for c in df.columns if c.endswith('_missing')]
        for col in missing_cols:
            df[col] = df[col].fillna(1).astype(int)
        return df

    def build(self, season_filter: int = None, stage_filter: str = None,
              start_year: int = None, end_year: int = None) -> dict:
        """Runs the pipeline and returns metadata about created files."""
        # 1. Load Data
        r_df = self.loader.load_session_results('R')
        q_df = self.loader.load_session_results('Q')
        s_df = self.loader.load_session_results('S')
        circuit_meta = self.loader.load_circuit_metadata()
        
        # Log loaded seasons
        loaded_seasons = set()
        if not r_df.empty:
            loaded_seasons.update(r_df['season'].unique())
        if not q_df.empty:
            loaded_seasons.update(q_df['season'].unique())
        print(f"\nSeasons loaded from ingested data: {sorted(loaded_seasons)}")
        
        # Check for requested seasons that are missing
        if start_year and end_year:
            requested = set(range(start_year, end_year + 1))
            missing = requested - loaded_seasons
            if missing:
                print(f"\n[WARNING] Requested seasons NOT found in ingested data: {sorted(missing)}")
                for y in sorted(missing):
                    print(f"  - Season {y}: No Q/R results parquet files found. Run ingestion first.")
        
        if r_df.empty:
            print("[ERROR] No race results loaded. Cannot build features.")
            return {"is_valid": False, "errors": ["No race data loaded"], "rows": {}}
        
        # 2. Build Historical Rollups (always use full history, filter later)
        db = DriverFeatureBuilder(r_df, q_df)
        driver_feats = db.build_features()
        
        tb = TeamFeatureBuilder(r_df, q_df)
        team_feats = tb.build_features()
        
        # 3. Build Targets
        tgb = TargetBuilder(r_df, q_df)
        targets = tgb.build_targets()
        
        # 4. Assemble Event Snapshots by Stage
        wb = WeekendFeatureBuilder(driver_feats, team_feats, circuit_meta)
        
        # Stage: pre_weekend (used to predict Qualifying)
        pre_weekend = wb.build_pre_weekend(r_df, s_df)
        
        # Stage: post_qualifying (used to predict Sprint, or Race if no sprint)
        post_qualifying = wb.build_post_qualifying(pre_weekend, q_df)
        
        # Stage: post_sprint (used to predict Race if sprint weekend)
        post_sprint = wb.build_post_sprint(post_qualifying, s_df)
        
        # 5. Map Stages to Target Datasets
        # Qualifying Features: pre_weekend stage (only historical + circuit data)
        qualifying_features = pre_weekend.copy()
        
        # Sprint Features: post_qualifying for sprint weekends
        sprint_features = pd.DataFrame()
        if not post_qualifying.empty:
            sprint_features = post_qualifying[post_qualifying['sprint_weekend_flag'] == 1].copy()
            
        # Race Features: pre_weekend, post_qualifying (for regular), post_sprint (for sprint)
        race_features_parts = []
        if not pre_weekend.empty:
            race_features_parts.append(pre_weekend.copy())
            
        if not post_qualifying.empty:
            reg = post_qualifying[post_qualifying['sprint_weekend_flag'] == 0].copy()
            race_features_parts.append(reg)
            
        if not post_sprint.empty:
            spr = post_sprint.copy()
            race_features_parts.append(spr)
            
        if race_features_parts:
            race_features = pd.concat(race_features_parts, ignore_index=True)
        else:
            race_features = pd.DataFrame()
        
        # Ensure qualifying and sprint columns exist on all race feature rows (with proper missing indicators)
        race_features = self._ensure_qualifying_columns(race_features)
        race_features = self._ensure_sprint_columns(race_features)
        
        # Fix all missing indicators across all tables
        qualifying_features = self._fix_all_missing_indicators(qualifying_features)
        race_features = self._fix_all_missing_indicators(race_features)
        sprint_features = self._fix_all_missing_indicators(sprint_features)
                
        # 6. Apply Filters (Season/Stage/Year Range)
        def apply_season_filter(df, sf=None, sy=None, ey=None):
            if df.empty:
                return df
            if sf:
                df = df[df['season'] == sf]
            if sy:
                df = df[df['season'] >= sy]
            if ey:
                df = df[df['season'] <= ey]
            return df
        
        qualifying_features = apply_season_filter(qualifying_features, season_filter, start_year, end_year)
        race_features = apply_season_filter(race_features, season_filter, start_year, end_year)
        sprint_features = apply_season_filter(sprint_features, season_filter, start_year, end_year)
        targets = apply_season_filter(targets, season_filter, start_year, end_year)
                
        if stage_filter:
            if stage_filter == 'pre_weekend':
                race_features = pd.DataFrame()
                sprint_features = pd.DataFrame()
            elif stage_filter == 'post_qualifying':
                qualifying_features = pd.DataFrame()
            elif stage_filter == 'post_sprint':
                qualifying_features = pd.DataFrame()
                race_features = pd.DataFrame()
                
        # 7. Validate Leakage
        validator = LeakageValidator(targets, qualifying_features, race_features, sprint_features)
        is_valid = validator.validate()
        
        # 8. Save Artifacts
        out_paths = {}
        
        if not qualifying_features.empty:
            p = self.out_dir / "qualifying_features.parquet"
            qualifying_features.to_parquet(p)
            out_paths['qualifying_features'] = str(p)
            
        if not race_features.empty:
            p = self.out_dir / "race_features.parquet"
            race_features.to_parquet(p)
            out_paths['race_features'] = str(p)
            
        if not sprint_features.empty:
            p = self.out_dir / "sprint_features.parquet"
            sprint_features.to_parquet(p)
            out_paths['sprint_features'] = str(p)
            
        if not targets.empty:
            p = self.out_dir / "targets.parquet"
            targets.to_parquet(p)
            out_paths['targets'] = str(p)
            
        # Metadata
        metadata = {
            "is_valid": is_valid,
            "errors": validator.errors,
            "rows": {
                "qualifying_features": len(qualifying_features) if not qualifying_features.empty else 0,
                "race_features": len(race_features) if not race_features.empty else 0,
                "sprint_features": len(sprint_features) if not sprint_features.empty else 0,
                "targets": len(targets) if not targets.empty else 0
            },
            "skipped_events": self.loader.skipped_events,
        }
        
        with open(self.out_dir / "leakage_report.json", "w") as f:
            json.dump({"is_valid": is_valid, "errors": validator.errors}, f, indent=4)
            
        with open(self.out_dir / "feature_metadata.json", "w") as f:
            json.dump(metadata, f, indent=4)
            
        out_paths['leakage_report'] = str(self.out_dir / "leakage_report.json")
        out_paths['feature_metadata'] = str(self.out_dir / "feature_metadata.json")
        out_paths['feature_schema'] = str(self.out_dir / "feature_schema.json")
        
        return metadata
