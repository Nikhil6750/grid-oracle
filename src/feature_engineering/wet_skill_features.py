import pandas as pd
import numpy as np

class WetSkillFeatureBuilder:
    def __init__(self, r_results_df: pd.DataFrame, r_weather_index: pd.DataFrame):
        self.r_results = r_results_df.copy()
        self.weather_index = r_weather_index.copy()

    def build_features(self) -> pd.DataFrame:
        if self.r_results.empty or self.weather_index.empty:
            return pd.DataFrame()

        # Merge weather flag onto results
        # weather_index has columns: season, round, weather_rainfall_flag
        df = self.r_results.merge(
            self.weather_index[['season', 'round', 'weather_rainfall_flag']],
            on=['season', 'round'], how='left'
        )
        
        # We need a temporal sorting to use shift(1)
        df = df.sort_values(['season', 'round'])
        
        # Prepare position
        df['Position'] = pd.to_numeric(df['Position'], errors='coerce')
        df['is_podium'] = (df['Position'] <= 3).astype(int)
        
        features = []
        for driver, drv_df in df.groupby('driver_code'):
            drv_df = drv_df.sort_values(['season', 'round']).copy()
            
            # Cumulative career average finish up to before this race
            career_avg_finish = drv_df['Position'].shift(1).expanding(min_periods=1).mean()
            
            # Isolate wet races
            is_wet = drv_df['weather_rainfall_flag'] == 1
            
            # Calculate wet stats
            # To get shift(1) correctly for wet races only, we map to the whole dataframe:
            wet_positions = drv_df['Position'].where(is_wet)
            wet_podiums = drv_df['is_podium'].where(is_wet)
            
            wet_count = is_wet.shift(1).cumsum().fillna(0)
            wet_avg_finish = wet_positions.shift(1).expanding(min_periods=1).mean()
            wet_podium_rate = wet_podiums.shift(1).expanding(min_periods=1).mean()
            
            # Dry stats
            is_dry = drv_df['weather_rainfall_flag'] == 0
            dry_positions = drv_df['Position'].where(is_dry)
            dry_avg_finish = dry_positions.shift(1).expanding(min_periods=1).mean()
            
            wet_vs_dry_delta = wet_avg_finish - dry_avg_finish
            
            # Composite skill score
            # if wet_race_count < 3, use career avg; else rolling last 5 wet
            last_5_wet = wet_positions.shift(1).rolling(window=5, min_periods=1).mean()
            
            skill_score = pd.Series(index=drv_df.index, dtype=float)
            mask_lt_3 = wet_count < 3
            skill_score[mask_lt_3] = career_avg_finish[mask_lt_3]
            skill_score[~mask_lt_3] = last_5_wet[~mask_lt_3]
            
            drv_df['driver_wet_race_count'] = wet_count
            drv_df['driver_wet_avg_finish'] = wet_avg_finish
            drv_df['driver_wet_podium_rate'] = wet_podium_rate
            drv_df['driver_wet_vs_dry_delta'] = wet_vs_dry_delta
            drv_df['driver_wet_skill_score'] = skill_score
            
            features.append(drv_df[['season', 'round', 'driver_code',
                                    'driver_wet_race_count', 'driver_wet_avg_finish',
                                    'driver_wet_podium_rate', 'driver_wet_vs_dry_delta',
                                    'driver_wet_skill_score']])
                                    
        out_df = pd.concat(features, ignore_index=True)
        
        # Missing indicators
        # If count < 3, we treat it as "missing true wet skill" for the model to learn
        out_df['driver_wet_race_count_missing'] = (out_df['driver_wet_race_count'] < 3).astype(int)
        
        num_cols = [
            'driver_wet_race_count', 'driver_wet_avg_finish',
            'driver_wet_podium_rate', 'driver_wet_vs_dry_delta',
            'driver_wet_skill_score'
        ]
        
        for col in num_cols:
            if col != 'driver_wet_race_count':
                out_df[f'{col}_missing'] = out_df[col].isna().astype(int)
            out_df[col] = out_df[col].fillna(out_df[col].median())
            
        return out_df
