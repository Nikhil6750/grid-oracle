import datetime
import numpy as np
import pandas as pd


class WeekendFeatureBuilder:
    """Assembles features strictly by prediction stage."""
    
    def __init__(self, driver_features: pd.DataFrame, team_features: pd.DataFrame, circuit_features: pd.DataFrame):
        self.driver_features = driver_features
        self.team_features = team_features
        self.circuit_features = circuit_features
        
    def _create_base_skeleton(self, base_df: pd.DataFrame, stage: str) -> pd.DataFrame:
        df = base_df.copy()
        df['prediction_stage'] = stage
        df['feature_cutoff_stage'] = stage
        df['feature_cutoff_timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return df

    def build_pre_weekend(self, results_df: pd.DataFrame, sprints_df: pd.DataFrame = None) -> pd.DataFrame:
        """Builds pre-weekend features using only historical rollups and static circuit data."""
        if results_df.empty:
            return pd.DataFrame()
            
        # Extract unique entries for the weekend skeleton
        base = results_df[['season', 'round', 'event_name', 'driver_number', 'driver_code', 'team']].drop_duplicates()
        
        # Determine if it's a sprint weekend
        if sprints_df is not None and not sprints_df.empty:
            sprint_events = sprints_df[['season', 'round']].drop_duplicates()
            sprint_events['sprint_weekend_flag'] = 1
            base = base.merge(sprint_events, on=['season', 'round'], how='left')
            base['sprint_weekend_flag'] = base['sprint_weekend_flag'].fillna(0).astype(int)
        else:
            base['sprint_weekend_flag'] = 0
            
        df = self._create_base_skeleton(base, 'pre_weekend')
        df['feature_source_sessions'] = 'historical_only'
        
        # Merge driver rollups
        if not self.driver_features.empty:
            df = df.merge(self.driver_features, on=['season', 'round', 'driver_code'], how='left')
            
        # Merge team rollups
        if not self.team_features.empty:
            df = df.merge(self.team_features, on=['season', 'round', 'team'], how='left')
            
        # Merge circuit metadata
        if not self.circuit_features.empty:
            from src.feature_engineering.circuit_features import CircuitFeatureBuilder
            cb = CircuitFeatureBuilder(self.circuit_features)
            df = cb.add_circuit_features(df)
            
        if 'driver_season_points_before_event' in df.columns:
            df['driver_championship_rank_before_event'] = (
                df.groupby(['season', 'round'])['driver_season_points_before_event']
                .rank(ascending=False, method='min')
            )
        else:
            df['driver_championship_rank_before_event'] = np.nan
        df['driver_championship_rank_before_event'] = df['driver_championship_rank_before_event'].fillna(11)

        if 'team_season_points_before_event' in df.columns:
            df['team_constructor_rank_before_event'] = (
                df.groupby(['season', 'round'])['team_season_points_before_event']
                .rank(ascending=False, method='min')
            )
        else:
            df['team_constructor_rank_before_event'] = np.nan
        df['team_constructor_rank_before_event'] = df['team_constructor_rank_before_event'].fillna(6)

        def _get_era(season):
            if season <= 2021: return 0
            elif season <= 2025: return 1
            else: return 2
        df['season_regulation_era'] = df['season'].apply(_get_era)
            
        return df

    def build_post_qualifying(self, pre_weekend_df: pd.DataFrame, quali_df: pd.DataFrame) -> pd.DataFrame:
        """Builds post-qualifying features, adding same-weekend qualifying data."""
        if pre_weekend_df.empty:
            return pd.DataFrame()
            
        df = pre_weekend_df.copy()
        df['prediction_stage'] = 'post_qualifying'
        df['feature_cutoff_stage'] = 'post_qualifying'
        df['feature_source_sessions'] = 'historical_only,Q'
        
        if quali_df is None or quali_df.empty:
            # Impute missing values if we don't have Q data
            for col in ['qualifying_position', 'qualifying_gap_to_pole', 'teammate_qualifying_delta', 'team_qualifying_rank', 'driver_qualified_ahead_of_teammate']:
                df[f'{col}_missing'] = 1
            df['qualifying_position'] = 10.0
            df['qualifying_gap_to_pole'] = 0.0
            df['teammate_qualifying_delta'] = 0.0
            df['team_qualifying_rank'] = 5
            df['driver_qualified_ahead_of_teammate'] = 0
            return df
            
        # Calculate qualifying features
        q = quali_df[['season', 'round', 'driver_code', 'Position', 'Time', 'team']].copy()
        q = q.rename(columns={'Position': 'qualifying_position'})
        
        # Gap to pole
        pole_times = q.groupby(['season', 'round'])['Time'].transform('min')
        q['qualifying_gap_to_pole'] = q['Time'] - pole_times
        q['qualifying_gap_to_pole'] = q['qualifying_gap_to_pole'].fillna(0) # for those without times
        
        # Teammate delta & qualified ahead
        # First, rank within team
        q['team_rank'] = q.groupby(['season', 'round', 'team'])['qualifying_position'].rank()
        q['driver_qualified_ahead_of_teammate'] = (q['team_rank'] == 1.0).astype(int)
        
        # For teammate delta, we find the min time for the team and subtract
        team_min_times = q.groupby(['season', 'round', 'team'])['Time'].transform('min')
        q['teammate_qualifying_delta'] = q['Time'] - team_min_times
        q['teammate_qualifying_delta'] = q['teammate_qualifying_delta'].fillna(0)
        
        # Team qualifying rank (average position of team cars)
        team_avg_q = q.groupby(['season', 'round', 'team'])['qualifying_position'].mean().reset_index()
        team_avg_q['team_qualifying_rank'] = team_avg_q.groupby(['season', 'round'])['qualifying_position'].rank().astype(int)
        team_avg_q = team_avg_q.drop(columns=['qualifying_position'])
        
        q = q.merge(team_avg_q, on=['season', 'round', 'team'], how='left')
        
        q_features = q[['season', 'round', 'driver_code', 'qualifying_position', 
                        'qualifying_gap_to_pole', 'teammate_qualifying_delta', 
                        'team_qualifying_rank', 'driver_qualified_ahead_of_teammate']]
                        
        df = df.merge(q_features, on=['season', 'round', 'driver_code'], how='left')
        
        q_cols_to_check = ['qualifying_position', 'qualifying_gap_to_pole', 'teammate_qualifying_delta', 'team_qualifying_rank', 'driver_qualified_ahead_of_teammate']
        for col in q_cols_to_check:
            df[f'{col}_missing'] = df[col].isna().astype(int)
        
        # Impute missing if driver DNS qualifying
        df['qualifying_position'] = df['qualifying_position'].fillna(20.0)
        df['qualifying_gap_to_pole'] = df['qualifying_gap_to_pole'].fillna(5.0)
        df['teammate_qualifying_delta'] = df['teammate_qualifying_delta'].fillna(0.0)
        df['team_qualifying_rank'] = df['team_qualifying_rank'].fillna(10)
        df['driver_qualified_ahead_of_teammate'] = df['driver_qualified_ahead_of_teammate'].fillna(0)
        
        return df

    def build_post_sprint(self, post_qualifying_df: pd.DataFrame, sprint_df: pd.DataFrame) -> pd.DataFrame:
        """Builds post-sprint features, adding same-weekend sprint data for sprint weekends only."""
        if post_qualifying_df.empty:
            return pd.DataFrame()
            
        # Only keep sprint weekends
        sprint_weekends = post_qualifying_df[post_qualifying_df['sprint_weekend_flag'] == 1].copy()
        if sprint_weekends.empty:
            return pd.DataFrame()
            
        df = sprint_weekends.copy()
        df['prediction_stage'] = 'post_sprint'
        df['feature_cutoff_stage'] = 'post_sprint'
        df['feature_source_sessions'] = 'historical_only,Q,S'
        
        if sprint_df is None or sprint_df.empty:
            for col in ['sprint_position', 'sprint_points', 'sprint_finish_status', 'sprint_position_gain_loss']:
                df[f'{col}_missing'] = 1
            df['sprint_position'] = 20.0
            df['sprint_points'] = 0.0
            df['sprint_finish_status'] = 'Unknown'
            df['sprint_position_gain_loss'] = 0.0
            return df
            
        s = sprint_df[['season', 'round', 'driver_code', 'Position', 'GridPosition', 'Points', 'Status']].copy()
        s = s.rename(columns={
            'Position': 'sprint_position',
            'Points': 'sprint_points',
            'Status': 'sprint_finish_status'
        })
        
        s['sprint_position_gain_loss'] = s['GridPosition'] - s['sprint_position']
        
        s_features = s[['season', 'round', 'driver_code', 'sprint_position', 'sprint_points', 
                        'sprint_finish_status', 'sprint_position_gain_loss']]
                        
        df = df.merge(s_features, on=['season', 'round', 'driver_code'], how='left')
        
        for col in ['sprint_position', 'sprint_points', 'sprint_finish_status', 'sprint_position_gain_loss']:
            df[f'{col}_missing'] = df[col].isna().astype(int)
            
        df['sprint_position'] = df['sprint_position'].fillna(20.0)
        df['sprint_points'] = df['sprint_points'].fillna(0.0)
        df['sprint_finish_status'] = df['sprint_finish_status'].fillna('Unknown')
        df['sprint_position_gain_loss'] = df['sprint_position_gain_loss'].fillna(0.0)
        
        return df
