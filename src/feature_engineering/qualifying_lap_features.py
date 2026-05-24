import pandas as pd
import numpy as np

class QualifyingLapFeatureBuilder:
    def __init__(self, q_laps_df: pd.DataFrame, q_results_df: pd.DataFrame = None):
        self.q_laps = q_laps_df.copy()
        self.q_results = q_results_df

    def build_features(self) -> pd.DataFrame:
        if self.q_laps.empty:
            return pd.DataFrame()

        # Clean laps logic
        # Clean lap = IsPersonalBest or LapTime not NaN, not Deleted
        is_clean = (self.q_laps['LapTime'].notna()) & (self.q_laps.get('Deleted', False) == False)
        clean_laps = self.q_laps[is_clean].copy()
        
        # Ensure laptime is seconds
        if pd.api.types.is_timedelta64_dtype(clean_laps['LapTime']):
            clean_laps['LapTime_s'] = clean_laps['LapTime'].dt.total_seconds()
        else:
            clean_laps['LapTime_s'] = clean_laps['LapTime'].astype(float)

        # Same for sectors
        for sec in ['Sector1Time', 'Sector2Time', 'Sector3Time']:
            if sec in clean_laps.columns:
                if pd.api.types.is_timedelta64_dtype(clean_laps[sec]):
                    clean_laps[f'{sec}_s'] = clean_laps[sec].dt.total_seconds()
                else:
                    clean_laps[f'{sec}_s'] = clean_laps[sec].astype(float)
            else:
                clean_laps[f'{sec}_s'] = np.nan

        features = []
        for (season, round_num), session_df in clean_laps.groupby(['season', 'round']):
            session_min_time = session_df['LapTime_s'].min()

            for driver, drv_df in session_df.groupby('driver_code'):
                best_lap = drv_df['LapTime_s'].min()
                gap_to_pole = best_lap - session_min_time
                gap_pct = (gap_to_pole / session_min_time) * 100 if session_min_time > 0 else 0

                row = {
                    'season': season,
                    'round': round_num,
                    'driver_code': driver,
                    'quali_best_lap_time_s': best_lap,
                    'quali_gap_to_pole_s': gap_to_pole,
                    'quali_gap_to_pole_pct': gap_pct,
                    'quali_best_sector1_s': drv_df['Sector1Time_s'].min() if 'Sector1Time_s' in drv_df else np.nan,
                    'quali_best_sector2_s': drv_df['Sector2Time_s'].min() if 'Sector2Time_s' in drv_df else np.nan,
                    'quali_best_sector3_s': drv_df['Sector3Time_s'].min() if 'Sector3Time_s' in drv_df else np.nan,
                    'quali_laps_completed': len(drv_df),
                    'quali_consistency_score': drv_df['LapTime_s'].std() if len(drv_df) > 1 else np.nan
                }
                features.append(row)

        out_df = pd.DataFrame(features)
        if out_df.empty:
            return out_df

        # Merge quali_session_reached if results are provided
        if self.q_results is not None and not self.q_results.empty:
            def _get_reached(pos):
                if pd.isna(pos): return np.nan
                pos = float(pos)
                if pos <= 10: return 3
                elif pos <= 15: return 2
                else: return 1
                
            res = self.q_results[['season', 'round', 'driver_code', 'Position']].copy()
            res['quali_session_reached'] = res['Position'].apply(_get_reached)
            res = res.drop(columns=['Position'])
            out_df = out_df.merge(res, on=['season', 'round', 'driver_code'], how='left')
        else:
            out_df['quali_session_reached'] = np.nan

        # Missing indicators and imputation
        num_cols = [
            'quali_best_lap_time_s', 'quali_gap_to_pole_s', 'quali_gap_to_pole_pct',
            'quali_best_sector1_s', 'quali_best_sector2_s', 'quali_best_sector3_s',
            'quali_session_reached', 'quali_laps_completed', 'quali_consistency_score'
        ]

        for col in num_cols:
            missing_col = f'{col}_missing'
            out_df[missing_col] = out_df[col].isna().astype(int)
            out_df[col] = out_df[col].fillna(out_df[col].median())

        return out_df
