import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.base import BaseEstimator, TransformerMixin

class LeakageGuard(BaseEstimator, TransformerMixin):
    """Hard target leakage guard. Fails if X contains forbidden columns."""
    def __init__(self, stage):
        self.stage = stage
        
    def fit(self, X, y=None):
        self._check_leakage(X)
        return self
        
    def transform(self, X, y=None):
        self._check_leakage(X)
        return X
        
    def _check_leakage(self, X):
        forbidden_exact = [
            'race_finish_position', 'finishing_position', 'classified_position',
            'classifiedposition', 'position', 'points', 'status', 'podium',
            'top10', 'winner', 'result', 'grid_position', 'race_result'
        ]
        
        for col in X.columns:
            c = col.lower()
            
            # Substring / pattern matches
            if c.startswith('target_') or '_target' in c:
                raise ValueError(f"Leakage detected: target column '{col}' found in model input X.")
                
            # Exceptions
            if c in ['qualifying_position', 'qualifying_position_missing']:
                if self.stage not in ['post_qualifying', 'post_sprint']:
                    raise ValueError(f"Leakage detected: '{col}' found in stage '{self.stage}'.")
                continue
                
            if c in ['sprint_position', 'sprint_points', 'sprint_position_missing', 'sprint_points_missing', 'sprint_finish_status']:
                if self.stage != 'post_sprint':
                    raise ValueError(f"Leakage detected: '{col}' found in stage '{self.stage}'.")
                continue
                
            # Exact matches
            if c in forbidden_exact:
                raise ValueError(f"Leakage detected: forbidden column '{col}' found in model input X.")

class FeatureSelector(BaseEstimator, TransformerMixin):
    """Selects specific columns to keep or drop."""
    def __init__(self, cols_to_drop=None):
        self.cols_to_drop = cols_to_drop or []
        
    def fit(self, X, y=None):
        return self
        
    def transform(self, X, y=None):
        X_copy = X.copy()
        # Drop only if column exists
        to_drop = [c for c in self.cols_to_drop if c in X_copy.columns]
        if to_drop:
            X_copy = X_copy.drop(columns=to_drop)
        return X_copy

class StageFeatureDropper(BaseEstimator, TransformerMixin):
    """Drops columns that are forbidden for the given prediction stage."""
    def __init__(self, stage):
        self.stage = stage
        self.dropped_cols_ = []
        
    def fit(self, X, y=None):
        self._set_drops(X)
        return self
        
    def transform(self, X, y=None):
        X_copy = X.copy()
        if not hasattr(self, 'dropped_cols_'):
            self._set_drops(X_copy)
            
        if self.dropped_cols_:
            X_copy = X_copy.drop(columns=[c for c in self.dropped_cols_ if c in X_copy.columns])
        return X_copy
        
    def _set_drops(self, X):
        to_drop = []
        if self.stage == 'pre_weekend':
            for col in X.columns:
                c = col.lower()
                if c.startswith('qualifying_') or c.startswith('sprint_') or c in [
                    'teammate_qualifying_delta', 'team_qualifying_rank', 'driver_qualified_ahead_of_teammate'
                ]:
                    to_drop.append(col)
        elif self.stage == 'post_qualifying':
            for col in X.columns:
                c = col.lower()
                if c.startswith('sprint_'):
                    to_drop.append(col)
                    
        self.dropped_cols_ = list(set(to_drop))

class DynamicPreprocessor(BaseEstimator, TransformerMixin):
    def __init__(self, cat_features, drop_features):
        self.cat_features = cat_features
        self.drop_features = drop_features
        self.preprocessor = None
        
    def fit(self, X, y=None):
        active_drop = [c for c in self.drop_features if c in X.columns]
        X_reduced = X.drop(columns=active_drop)
        
        active_cat = [c for c in self.cat_features if c in X_reduced.columns]
        active_num = [c for c in X_reduced.columns if c not in active_cat and pd.api.types.is_numeric_dtype(X_reduced[c])]
        
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])

        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])
        
        transformers = []
        if active_num:
            transformers.append(('num', numeric_transformer, active_num))
        if active_cat:
            transformers.append(('cat', categorical_transformer, active_cat))
            
        self.preprocessor = ColumnTransformer(transformers=transformers, remainder='drop')
        self.preprocessor.fit(X_reduced, y)
        return self
        
    def transform(self, X, y=None):
        active_drop = [c for c in self.drop_features if c in X.columns]
        X_reduced = X.drop(columns=active_drop)
        return self.preprocessor.transform(X_reduced)

def get_baseline_pipeline(model, stage, cat_cols=None, num_cols=None, cols_to_drop=None):
    """
    Returns an sklearn Pipeline with standard preprocessing for baseline models.
    """
    if cat_cols is None:
        cat_cols = ['team', 'team_name', 'track_type', 'tyre_degradation_category', 'prediction_stage', 'feature_cutoff_stage', 'sprint_finish_status']
    
    if cols_to_drop is None:
        cols_to_drop = [
            'season', 'round', 'event_name', 'driver_code', 'driver_number', 
            'feature_source_sessions', 'feature_cutoff_timestamp',
            'target_qualifying_position', 'target_race_finish_position',
            'target_podium_class', 'target_top10', 'target_points_finish', 'target_dnf',
            'target_podium_binary'
        ]
        
    pipeline = Pipeline(steps=[
        ('feature_selector', FeatureSelector(cols_to_drop=cols_to_drop)),
        ('stage_dropper', StageFeatureDropper(stage=stage)),
        ('leakage_guard', LeakageGuard(stage=stage)),
        ('preprocessor', DynamicPreprocessor(cat_cols, cols_to_drop)),
        ('model', model)
    ])
    
    return pipeline
