import pandas as pd
import numpy as np

class WeatherFeatureBuilder:
    def __init__(self, weather_df: pd.DataFrame, session_type: str):
        self.weather_df = weather_df.copy()
        self.session_type = session_type

    def build_features(self) -> pd.DataFrame:
        if self.weather_df.empty:
            return pd.DataFrame()

        # Group by season and round
        features = []
        for (season, round_num), df_group in self.weather_df.groupby(['season', 'round']):
            # Filter logic (e.g. Q3 time window) could be complex without Q laps timing
            # Using entire session as fallback approximation which covers most needs
            
            # Numeric conversion to be safe
            for col in ['AirTemp', 'TrackTemp', 'Humidity', 'WindSpeed']:
                if col in df_group.columns:
                    df_group[col] = pd.to_numeric(df_group[col], errors='coerce')
            
            air_temp_avg = df_group['AirTemp'].mean() if 'AirTemp' in df_group.columns else np.nan
            track_temp_avg = df_group['TrackTemp'].mean() if 'TrackTemp' in df_group.columns else np.nan
            humidity_avg = df_group['Humidity'].mean() if 'Humidity' in df_group.columns else np.nan
            wind_speed_avg = df_group['WindSpeed'].mean() if 'WindSpeed' in df_group.columns else np.nan
            
            rainfall_flag = 0
            max_rainfall_minutes = 0
            if 'Rainfall' in df_group.columns:
                # FastF1 Rainfall is boolean
                is_raining = df_group['Rainfall'] == True
                if is_raining.any():
                    rainfall_flag = 1
                # Usually weather is sampled every minute
                max_rainfall_minutes = is_raining.sum()

            track_temp_delta = np.nan
            if 'TrackTemp' in df_group.columns:
                track_temp_delta = df_group['TrackTemp'].max() - df_group['TrackTemp'].min()

            row = {
                'season': season,
                'round': round_num,
                'weather_air_temp_avg': air_temp_avg,
                'weather_track_temp_avg': track_temp_avg,
                'weather_humidity_avg': humidity_avg,
                'weather_wind_speed_avg': wind_speed_avg,
                'weather_rainfall_flag': rainfall_flag,
                'weather_max_rainfall_minutes': max_rainfall_minutes,
                'weather_track_temp_delta': track_temp_delta
            }
            features.append(row)

        out_df = pd.DataFrame(features)
        
        # Missing indicators
        num_cols = [
            'weather_air_temp_avg', 'weather_track_temp_avg', 'weather_humidity_avg',
            'weather_wind_speed_avg', 'weather_rainfall_flag', 'weather_max_rainfall_minutes',
            'weather_track_temp_delta'
        ]

        for col in num_cols:
            if col in out_df.columns:
                missing_col = f'{col}_missing'
                out_df[missing_col] = out_df[col].isna().astype(int)
                out_df[col] = out_df[col].fillna(out_df[col].median())

        return out_df
