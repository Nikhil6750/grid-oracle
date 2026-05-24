import pandas as pd

class NewsFeatureBuilder:
    def __init__(self, news_dict: dict, driver_codes: list):
        self.news = news_dict
        self.driver_codes = driver_codes

    def build_features(self) -> pd.DataFrame:
        features = []
        
        # Determine if data was successfully fetched
        # An empty dict or dict with only default 0.0 values implies failure or no news
        data_available = 1 if self.news and ("grid_penalties" in self.news or "wet_race_probability" in self.news) else 0
        
        penalties = self.news.get("grid_penalties", {})
        wet_prob = self.news.get("wet_race_probability", 0.0)
        sc_prob = self.news.get("safety_car_probability", 0.0)
        
        for code in self.driver_codes:
            drops = penalties.get(code, 0)
            flag = 1 if drops > 0 else 0
            
            features.append({
                'driver_code': code,
                'news_grid_penalty_positions': drops,
                'news_grid_penalty_flag': flag,
                'news_wet_race_probability': wet_prob,
                'news_safety_car_probability': sc_prob,
                'news_data_available': data_available
            })
            
        out_df = pd.DataFrame(features)
        if out_df.empty:
            return out_df
            
        num_cols = [
            'news_grid_penalty_positions', 'news_grid_penalty_flag',
            'news_wet_race_probability', 'news_safety_car_probability',
            'news_data_available'
        ]
        
        for col in num_cols:
            out_df[f'{col}_missing'] = out_df[col].isna().astype(int)
            out_df[col] = out_df[col].fillna(0.0)
            
        return out_df
