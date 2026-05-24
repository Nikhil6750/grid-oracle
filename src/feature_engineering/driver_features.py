import numpy as np
import pandas as pd


class DriverFeatureBuilder:
    """Builds historical driver features strictly preventing data leakage."""
    
    def __init__(self, results_df: pd.DataFrame, quali_df: pd.DataFrame = None):
        self.results = results_df.copy()
        self.quali = quali_df.copy() if quali_df is not None and not quali_df.empty else pd.DataFrame()
        
    def _is_dnf(self, status: str) -> int:
        if pd.isna(status):
            return 0
        status_lower = str(status).lower()
        non_dnf_statuses = ['finished', '+1 lap', '+2 laps', '+3 laps', '+4 laps', '+5 laps', '+6 laps']
        if any(s in status_lower for s in non_dnf_statuses):
            return 0
        return 1

    def build_features(self) -> pd.DataFrame:
        if self.results.empty:
            return pd.DataFrame()
            
        # Ensure we have the base dataframe structured chronologically
        cols_needed = ['season', 'round', 'event_name', 'driver_code', 'Position', 'Points', 'Status']
        available_cols = [c for c in cols_needed if c in self.results.columns]
        df = self.results[available_cols].copy()
        
        if 'Status' in df.columns:
            df['is_dnf'] = df['Status'].apply(self._is_dnf)
        else:
            df['is_dnf'] = 0
            
        if 'Points' not in df.columns:
            df['Points'] = 0.0
            
        if 'Position' not in df.columns:
            df['Position'] = 10.0
        
        # Merge qualifying positions if available
        if not self.quali.empty:
            q_cols = ['season', 'round', 'driver_code', 'Position']
            q_avail = [c for c in q_cols if c in self.quali.columns]
            q_df = self.quali[q_avail].rename(columns={'Position': 'quali_position'})
            df = df.merge(q_df, on=['season', 'round', 'driver_code'], how='left')
        else:
            df['quali_position'] = np.nan
            
        df = df.sort_values(['season', 'round'])
        
        features = []
        
        for driver, driver_df in df.groupby('driver_code'):
            driver_df = driver_df.sort_values(['season', 'round']).reset_index(drop=True)
            
            # Shifting prevents leakage: metrics for current race use only previous races
            shifted_points = driver_df['Points'].shift(1)
            shifted_finish = driver_df['Position'].shift(1)
            shifted_quali = driver_df['quali_position'].shift(1)
            shifted_dnf = driver_df['is_dnf'].shift(1)
            
            last_5_points_avg = shifted_points.rolling(window=5, min_periods=1).mean()
            last_5_finish_avg = shifted_finish.rolling(window=5, min_periods=1).mean()
            last_5_quali_avg = shifted_quali.rolling(window=5, min_periods=1).mean()
            last_5_dnf_rate = shifted_dnf.rolling(window=5, min_periods=1).mean()
            
            season_points_before = driver_df.groupby('season', group_keys=False)['Points'].apply(
                lambda x: x.shift(1).cumsum()
            )
            season_avg_finish = driver_df.groupby('season', group_keys=False)['Position'].apply(
                lambda x: x.shift(1).expanding().mean()
            )
            season_avg_quali = driver_df.groupby('season', group_keys=False)['quali_position'].apply(
                lambda x: x.shift(1).expanding().mean()
            )
            
            circuit_avg_finish = driver_df.groupby('event_name', group_keys=False)['Position'].apply(
                lambda x: x.shift(1).expanding().mean()
            )
            circuit_avg_quali = driver_df.groupby('event_name', group_keys=False)['quali_position'].apply(
                lambda x: x.shift(1).expanding().mean()
            )
            
            feature_df = pd.DataFrame({
                'season': driver_df['season'],
                'round': driver_df['round'],
                'driver_code': driver_df['driver_code'],
                'driver_last_5_points_avg': last_5_points_avg,
                'driver_last_5_finish_avg': last_5_finish_avg,
                'driver_last_5_qualifying_avg': last_5_quali_avg,
                'driver_last_5_dnf_rate': last_5_dnf_rate,
                'driver_season_points_before_event': season_points_before,
                'driver_season_avg_finish_before_event': season_avg_finish,
                'driver_season_avg_quali_before_event': season_avg_quali,
                'driver_circuit_avg_finish_before_event': circuit_avg_finish,
                'driver_circuit_avg_quali_before_event': circuit_avg_quali
            })
            
            features.append(feature_df)
            
        if not features:
            return pd.DataFrame()
            
        final_df = pd.concat(features, ignore_index=True)
        
        # Impute missing values and add missing indicators
        feature_cols = [
            'driver_last_5_points_avg', 'driver_last_5_finish_avg', 'driver_last_5_qualifying_avg', 'driver_last_5_dnf_rate',
            'driver_season_points_before_event', 'driver_season_avg_finish_before_event', 'driver_season_avg_quali_before_event',
            'driver_circuit_avg_finish_before_event', 'driver_circuit_avg_quali_before_event'
        ]
        
        for col in feature_cols:
            final_df[f"{col}_missing"] = final_df[col].isna().astype(int)
            if 'points' in col:
                final_df[col] = final_df[col].fillna(0.0)
            elif 'dnf' in col:
                final_df[col] = final_df[col].fillna(0.0)
            elif 'finish' in col or 'qualifying' in col or 'quali' in col:
                final_df[col] = final_df[col].fillna(10.0)
                
        return final_df
