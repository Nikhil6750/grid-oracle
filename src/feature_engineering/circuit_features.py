import pandas as pd


class CircuitFeatureBuilder:
    """Merges static circuit metadata into feature datasets."""
    
    def __init__(self, circuit_metadata_df: pd.DataFrame):
        self.circuit_meta = circuit_metadata_df.copy()
        
    def add_circuit_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Merges circuit metadata based on event_name."""
        if df.empty or self.circuit_meta.empty:
            return df
            
        # We join on event_name, but in real life event_name can have slight variations.
        # So we try to do a case-insensitive join.
        meta = self.circuit_meta.copy()
        meta['join_key'] = meta['event_name'].astype(str).str.lower().str.strip()
        
        df_copy = df.copy()
        df_copy['join_key'] = df_copy['event_name'].astype(str).str.lower().str.strip()
        
        # Merge left to keep all original rows
        merged = df_copy.merge(meta, on='join_key', how='left', suffixes=('', '_circuit'))
        
        # Drop join key and redundant columns
        merged = merged.drop(columns=['join_key', 'event_name_circuit', 'country_circuit'], errors='ignore')
        
        # Fill missing values if any event_name didn't match
        if 'tyre_degradation_category' in merged.columns:
            missing_mask = merged['tyre_degradation_category'].isna()
            if missing_mask.any():
                if 'circuit_id' in merged.columns:
                    merged.loc[missing_mask, 'circuit_id'] = 'unknown_circuit'
                merged.loc[missing_mask, 'tyre_degradation_category'] = 'Medium'
                merged.loc[missing_mask, 'tyre_degradation_level'] = 2
            
        return merged
