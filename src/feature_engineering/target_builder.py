import pandas as pd


class TargetBuilder:
    """Builds supervised target variables."""
    
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

    def build_targets(self) -> pd.DataFrame:
        if self.results.empty:
            return pd.DataFrame()
            
        cols_needed = ['season', 'round', 'event_name', 'driver_code', 'driver_number', 'Position', 'Points', 'Status']
        available_cols = [c for c in cols_needed if c in self.results.columns]
        df = self.results[available_cols].copy()
        
        # We need a strict drop of missing targets, so we only include races where we have a Position
        df = df.dropna(subset=['Position'])
        
        df['target_race_finish_position'] = df['Position']
        
        df['target_podium_class'] = df['Position'].apply(lambda x: x if x <= 3 else 4)
        
        df['target_top10'] = df['Position'].apply(lambda x: 1 if x <= 10 else 0)
        
        if 'Points' in df.columns:
            df['target_points_finish'] = df['Points'].apply(lambda x: 1 if x > 0 else 0)
        else:
            df['target_points_finish'] = pd.NA
            
        if 'Status' in df.columns:
            df['target_dnf'] = df['Status'].apply(self._is_dnf)
        else:
            df['target_dnf'] = pd.NA
            
        if not self.quali.empty:
            q_cols = ['season', 'round', 'driver_code', 'Position']
            q_avail = [c for c in q_cols if c in self.quali.columns]
            q_df = self.quali[q_avail].rename(columns={'Position': 'target_qualifying_position'})
            q_df = q_df.dropna(subset=['target_qualifying_position'])
            df = df.merge(q_df, on=['season', 'round', 'driver_code'], how='left')
        else:
            df['target_qualifying_position'] = pd.NA
            
        target_cols = [
            'season', 'round', 'event_name', 'driver_number', 'driver_code',
            'target_qualifying_position', 'target_race_finish_position', 
            'target_podium_class', 'target_top10', 'target_points_finish', 'target_dnf'
        ]
        
        # Only return the target columns and identifiers
        return df[[c for c in target_cols if c in df.columns]]
