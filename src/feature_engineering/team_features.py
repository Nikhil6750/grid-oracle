import numpy as np
import pandas as pd


class TeamFeatureBuilder:
    """Builds historical team features strictly preventing data leakage."""
    
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
            
        cols_needed = ['season', 'round', 'event_name', 'team', 'Position', 'Points', 'Status']
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
        
        # Aggregate driver results into team results per event
        team_event_df = df.groupby(['season', 'round', 'event_name', 'team']).agg(
            team_points=('Points', 'sum'),
            team_avg_finish=('Position', 'mean'),
            team_dnfs=('is_dnf', 'sum'),
            cars_entered=('is_dnf', 'count')
        ).reset_index()
        
        team_event_df['team_dnf_rate'] = team_event_df['team_dnfs'] / team_event_df['cars_entered']
        
        # Merge qualifying positions if available
        if not self.quali.empty:
            q_cols = ['season', 'round', 'team', 'Position']
            q_avail = [c for c in q_cols if c in self.quali.columns]
            q_df = self.quali[q_avail]
            team_q_df = q_df.groupby(['season', 'round', 'team']).agg(
                team_avg_quali=('Position', 'mean')
            ).reset_index()
            
            team_event_df = team_event_df.merge(team_q_df, on=['season', 'round', 'team'], how='left')
        else:
            team_event_df['team_avg_quali'] = np.nan
            
        team_event_df = team_event_df.sort_values(['season', 'round'])
        
        features = []
        
        for team, team_df in team_event_df.groupby('team'):
            team_df = team_df.sort_values(['season', 'round']).reset_index(drop=True)
            
            # Shifting prevents leakage
            shifted_points = team_df['team_points'].shift(1)
            shifted_finish = team_df['team_avg_finish'].shift(1)
            shifted_quali = team_df['team_avg_quali'].shift(1)
            shifted_dnf = team_df['team_dnf_rate'].shift(1)
            
            last_5_points_avg = shifted_points.rolling(window=5, min_periods=1).mean()
            last_5_finish_avg = shifted_finish.rolling(window=5, min_periods=1).mean()
            last_5_quali_avg = shifted_quali.rolling(window=5, min_periods=1).mean()
            
            season_points_before = team_df.groupby('season', group_keys=False)['team_points'].apply(
                lambda x: x.shift(1).cumsum()
            )
            season_avg_finish = team_df.groupby('season', group_keys=False)['team_avg_finish'].apply(
                lambda x: x.shift(1).expanding().mean()
            )
            season_avg_quali = team_df.groupby('season', group_keys=False)['team_avg_quali'].apply(
                lambda x: x.shift(1).expanding().mean()
            )
            team_dnf_rate_before = team_df.groupby('season', group_keys=False)['team_dnf_rate'].apply(
                lambda x: x.shift(1).expanding().mean()
            )
            
            feature_df = pd.DataFrame({
                'season': team_df['season'],
                'round': team_df['round'],
                'team': team_df['team'],
                'team_last_5_points_avg': last_5_points_avg,
                'team_last_5_finish_avg': last_5_finish_avg,
                'team_last_5_qualifying_avg': last_5_quali_avg,
                'team_season_points_before_event': season_points_before,
                'team_season_avg_finish_before_event': season_avg_finish,
                'team_season_avg_quali_before_event': season_avg_quali,
                'team_dnf_rate_before_event': team_dnf_rate_before
            })
            
            features.append(feature_df)
            
        if not features:
            return pd.DataFrame()
            
        final_df = pd.concat(features, ignore_index=True)
        
        feature_cols = [
            'team_last_5_points_avg', 'team_last_5_finish_avg', 'team_last_5_qualifying_avg', 
            'team_season_points_before_event', 'team_season_avg_finish_before_event', 
            'team_season_avg_quali_before_event', 'team_dnf_rate_before_event'
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
