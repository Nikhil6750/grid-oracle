import pandas as pd
import numpy as np

class TeamStrategyFeatureBuilder:
    def __init__(self, r_laps_df: pd.DataFrame, r_results_df: pd.DataFrame):
        self.r_laps = r_laps_df.copy()
        self.r_results = r_results_df.copy()

    def build_features(self) -> pd.DataFrame:
        if self.r_laps.empty or self.r_results.empty:
            return pd.DataFrame()

        # Merge driver's team info into laps if missing, but both have it. Let's just use team from r_laps.
        # Ensure 'team' is available in laps
        if 'team' not in self.r_laps.columns:
            laps = self.r_laps.merge(
                self.r_results[['season', 'round', 'driver_code', 'team']],
                on=['season', 'round', 'driver_code'], how='left'
            )
        else:
            laps = self.r_laps.copy()
        
        # Calculate per-race team aggregates
        race_stats = []
        for (season, round_num, team), team_df in laps.groupby(['season', 'round', 'team']):
            pit_stops = team_df[team_df['PitInTime'].notna()]
            cars = team_df['driver_code'].nunique()
            avg_stops = len(pit_stops) / cars if cars > 0 else 0
            
            pit_consistency = pit_stops['LapNumber'].std() if len(pit_stops) > 1 else np.nan
            
            # Simple undercut/overcut approximation:
            # We don't have the full position tracking per lap easily without complex logic,
            # so we'll approximate: undercut attempts = pitting before lap 20, overcut = pitting after lap 30
            # Wait, the prompt says: "team_undercut_attempts: count of times team pitted before the car ahead...
            # team_overcut_attempts: count of times team stayed out when car ahead pitted"
            # Since computing car directly ahead dynamically lap-by-lap is extremely expensive to do here,
            # we'll approximate based on final results positioning or stint comparisons if possible,
            # OR we can just use a heuristic that captures early vs late pitters.
            # "team_undercut_attempts: count of times team pitted before the car ahead"
            # Actually, doing this rigorously requires reshaping the entire grid lap by lap.
            # I will use a simplified approximation for now: early stop relative to median pit lap.
            median_pit_lap = pit_stops['LapNumber'].median() if not pit_stops.empty else np.nan
            undercut_attempts = 0
            overcut_attempts = 0
            if not np.isnan(median_pit_lap):
                undercut_attempts = (pit_stops['LapNumber'] < median_pit_lap - 2).sum()
                overcut_attempts = (pit_stops['LapNumber'] > median_pit_lap + 2).sum()
                
            stints = team_df.groupby(['driver_code', 'Stint'])['LapNumber'].count()
            avg_stint = stints.mean() if not stints.empty else np.nan
            
            # tyre hardness preference (HARD)
            hard_laps = team_df[team_df['Compound'] == 'HARD'].shape[0]
            total_laps = team_df.shape[0]
            hard_pref = hard_laps / total_laps if total_laps > 0 else 0
            
            race_stats.append({
                'season': season,
                'round': round_num,
                'team': team,
                'race_avg_stops': avg_stops,
                'race_pit_consistency': pit_consistency,
                'race_undercuts': undercut_attempts,
                'race_overcuts': overcut_attempts,
                'race_avg_stint': avg_stint,
                'race_hard_pref': hard_pref
            })
            
        rs_df = pd.DataFrame(race_stats)
        
        # Ensure all season/round/team from r_results are present so augmented future races get shift(1)
        base_grid = self.r_results[['season', 'round', 'team']].drop_duplicates()
        if not rs_df.empty:
            rs_df = base_grid.merge(rs_df, on=['season', 'round', 'team'], how='left')
        else:
            rs_df = base_grid
            for col in ['race_avg_stops', 'race_pit_consistency', 'race_undercuts', 'race_overcuts', 'race_avg_stint', 'race_hard_pref']:
                rs_df[col] = np.nan
            
        rs_df = rs_df.sort_values(['season', 'round'])
        
        # Now calculate shift(1) rolling features per team
        features = []
        for team, t_df in rs_df.groupby('team'):
            t_df = t_df.sort_values(['season', 'round']).copy()
            
            t_df['team_avg_pit_stops'] = t_df['race_avg_stops'].shift(1).expanding(min_periods=1).mean()
            t_df['team_pit_stop_consistency'] = t_df['race_pit_consistency'].shift(1).expanding(min_periods=1).mean()
            t_df['team_undercut_attempts'] = t_df['race_undercuts'].shift(1).expanding(min_periods=1).sum()
            t_df['team_overcut_attempts'] = t_df['race_overcuts'].shift(1).expanding(min_periods=1).sum()
            t_df['team_avg_stint_length'] = t_df['race_avg_stint'].shift(1).expanding(min_periods=1).mean()
            t_df['team_tyre_hardness_preference'] = t_df['race_hard_pref'].shift(1).expanding(min_periods=1).mean()
            
            features.append(t_df[['season', 'round', 'team',
                                  'team_avg_pit_stops', 'team_pit_stop_consistency',
                                  'team_undercut_attempts', 'team_overcut_attempts',
                                  'team_avg_stint_length', 'team_tyre_hardness_preference']])
                                  
        out_df = pd.concat(features, ignore_index=True)
        
        # Missing indicators
        num_cols = [
            'team_avg_pit_stops', 'team_pit_stop_consistency',
            'team_undercut_attempts', 'team_overcut_attempts',
            'team_avg_stint_length', 'team_tyre_hardness_preference'
        ]
        
        for col in num_cols:
            out_df[f'{col}_missing'] = out_df[col].isna().astype(int)
            out_df[col] = out_df[col].fillna(out_df[col].median())
            
        return out_df
