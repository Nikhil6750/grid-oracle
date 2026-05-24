import os
import sys
import json
import argparse
import datetime
import fastf1
import joblib
import pandas as pd
import numpy as np
import warnings
import pickle

# Must be before any other imports that depend on project structure
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_PATH = os.path.join(_PROJECT_ROOT, 'src')
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if os.path.exists(_SRC_PATH) and _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

_DEBUG_MODE = '--debug' in sys.argv
if _DEBUG_MODE:
    print(f"[PATH] Project root added: {_PROJECT_ROOT}")
    print(f"[PATH] src/ found: {os.path.exists(_SRC_PATH)}")

class SafeUnpickler(pickle.Unpickler):
    """
    Remaps missing src.* module references to builtins.
    Only used when normal joblib.load fails.
    """
    def find_class(self, module, name):
        # Remap any src.* module to a safe fallback
        if module.startswith('src.'):
            if _DEBUG_MODE:
                print(f"[REMAP] {module}.{name} → skipping custom class")
            # Return a generic object placeholder
            return object
        return super().find_class(module, name)

def safe_load_model(path):
    """Load a joblib model, falling back to safe unpickler if src.* missing."""
    try:
        return joblib.load(path)
    except ModuleNotFoundError as e:
        if 'src' in str(e):
            if _DEBUG_MODE:
                print(f"[WARN] Normal load failed ({e}), trying safe unpickler...")
            with open(path, 'rb') as f:
                return SafeUnpickler(f).load()
        raise

# Suppress warnings for clean output unless debug is requested
warnings.filterwarnings('ignore')

def main():
    parser = argparse.ArgumentParser(description="Grid Oracle 2026 Miami GP Prediction")
    parser.add_argument('--stage', type=str, default='post_qualifying', help="Prediction stage")
    parser.add_argument('--debug', action='store_true', help="Enable debug output")
    args = parser.parse_args()

    # =================================================================
    # PART 1 — AUTO-DISCOVER 2026 MIAMI SESSION IDENTIFIERS
    # =================================================================
    schedule = fastf1.get_event_schedule(2026, include_testing=False)
    miami_event = schedule[
        schedule['EventName'].str.contains('Miami', case=False, na=False)
    ]
    
    if miami_event.empty:
        print("[FATAL] Miami event not found for 2026 season.")
        sys.exit(1)
        
    miami_event = miami_event.iloc[0]

    SEASON = 2026
    ROUND = int(miami_event['RoundNumber'])
    EVENT_NAME = miami_event['EventName']

    if args.debug:
        print(f"[DISCOVERY] Season: {SEASON}")
        print(f"[DISCOVERY] Round: {ROUND}")
        print(f"[DISCOVERY] Event: {EVENT_NAME}")

    SESSIONS_TO_TRY = ['FP1', 'SQ', 'S', 'Q']
    loaded_sessions = {}
    failed_sessions = {}

    for session_name in SESSIONS_TO_TRY:
        try:
            sess = fastf1.get_session(SEASON, ROUND, session_name)
            sess.load(
                laps=True,
                telemetry=False,
                weather=False,
                messages=False
            )
            loaded_sessions[session_name] = sess
            if args.debug:
                print(f'[SESSION] Loaded: {session_name}')
        except Exception as e:
            failed_sessions[session_name] = str(e)
            if args.debug:
                print(f'[SESSION] Failed: {session_name} — {e}')

    if not loaded_sessions:
        print('[FATAL] No FastF1 sessions available. Cannot proceed.')
        sys.exit(1)

    # =================================================================
    # PART 2 — AUTO-EXTRACT DRIVER LIST FROM SESSIONS
    # =================================================================
    def get_drivers_from_session(sess):
        if hasattr(sess, 'results') and sess.results is not None and not sess.results.empty:
            return sess.results[
                ['DriverNumber','Abbreviation','FullName','TeamName']
            ].drop_duplicates()
        else:
            laps = sess.laps
            return laps[
                ['Driver','Team']
            ].drop_duplicates().rename(
                columns={'Driver':'Abbreviation','Team':'TeamName'}
            )

    drivers_df = pd.DataFrame()
    for name in ['Q', 'S', 'SQ', 'FP1']:
        if name in loaded_sessions:
            drivers_df = get_drivers_from_session(loaded_sessions[name])
            if args.debug:
                print(f'[DRIVERS] Extracted {len(drivers_df)} drivers from {name}')
            break

    if drivers_df.empty:
        print('[FATAL] Could not extract drivers from loaded sessions.')
        sys.exit(1)

    drivers_list = drivers_df['Abbreviation'].tolist()
    n_drivers = len(drivers_list)
    feature_dict = {driver: {} for driver in drivers_list}

    # =================================================================
    # PART 3 — AUTO-EXTRACT FEATURES FROM SESSIONS
    # =================================================================
    q_sess = loaded_sessions.get('Q')
    if q_sess:
        q_results = q_sess.results.copy()

        # ── DEBUG: show real columns from FastF1 ──────────────────────────────
        if args.debug:
            print(f"[DEBUG] Q session results columns: {list(q_results.columns)}")
            print(f"[DEBUG] Q session results dtypes:\n{q_results.dtypes}")

        # ── Get best lap time per driver from Q3 > Q2 > Q1 ───────────────────
        # FastF1 v3.x uses Q1/Q2/Q3 columns (pandas Timedelta), not BestLapTime
        def get_best_qualifying_time(row):
            for col in ['Q3', 'Q2', 'Q1']:
                if col in row.index:
                    val = row[col]
                    if pd.notna(val):
                        return val
            return pd.NaT

        q_results['_BestTime'] = q_results.apply(
            get_best_qualifying_time, axis=1
        )

        # ── Sort by Position column if it exists, else by best time ──────────
        if 'Position' in q_results.columns and q_results['Position'].notna().any():
            q_results = q_results.sort_values('Position').reset_index(drop=True)
        else:
            q_results = q_results.sort_values('_BestTime').reset_index(drop=True)

        # ── Helper: Timedelta → float seconds ────────────────────────────────
        def td_to_sec(td):
            try:
                if pd.isna(td):
                    return float('nan')
                return float(td.total_seconds())
            except Exception:
                return float('nan')

        # ── Pole time in seconds ──────────────────────────────────────────────
        pole_time_sec = td_to_sec(q_results.iloc[0]['_BestTime'])

        if args.debug:
            print(f"[DEBUG] Pole time (seconds): {pole_time_sec}")

        # ── Build qualifying features for each driver ─────────────────────────
        q_results['qualifying_position'] = range(1, len(q_results) + 1)

        q_results['best_lap_seconds'] = q_results['_BestTime'].apply(td_to_sec)

        q_results['gap_to_pole_seconds'] = q_results['best_lap_seconds'].apply(
            lambda s: round(s - pole_time_sec, 4) if not pd.isna(s) else float('nan')
        )

        # ── Q1/Q2/Q3 times as seconds (individual columns) ───────────────────
        for q_col in ['Q1', 'Q2', 'Q3']:
            sec_col = f'{q_col}_seconds'
            if q_col in q_results.columns:
                q_results[sec_col] = q_results[q_col].apply(td_to_sec)
            else:
                q_results[sec_col] = float('nan')

        # ── Populate feature_dict ─────────────────────────────────────────────
        for _, row in q_results.iterrows():
            abbr = row['Abbreviation']
            if abbr in feature_dict:
                feature_dict[abbr]['qualifying_position'] = row['qualifying_position']
                feature_dict[abbr]['gap_to_pole_seconds'] = row['gap_to_pole_seconds']

        # ── Print confirmation ────────────────────────────────────────────────
        print(f"[FEATURE] Q: qualifying_position extracted for {len(q_results)} drivers")
        print(
            f"[FEATURE] Q: gap_to_pole_seconds extracted for "
            f"{q_results['gap_to_pole_seconds'].notna().sum()} drivers"
        )

        if args.debug:
            cols_to_show = [
                c for c in [
                    'Abbreviation', 'FullName', 'TeamName',
                    'qualifying_position', 'best_lap_seconds', 'gap_to_pole_seconds'
                ] if c in q_results.columns
            ]
            print("\n[DEBUG] Q session extracted data:")
            print(q_results[cols_to_show].to_string(index=False))
            print()

    s_sess = loaded_sessions.get('S')
    if s_sess and hasattr(s_sess, 'results') and s_sess.results is not None:
        s_results = s_sess.results.sort_values('Position')
        for _, row in s_results.iterrows():
            abbr = row['Abbreviation']
            if abbr in feature_dict:
                feature_dict[abbr]['sprint_finish_position'] = row['Position']
        if args.debug:
            print(f'[FEATURE] S: sprint_finish_position extracted for {len(s_results)} drivers')

    sq_sess = loaded_sessions.get('SQ')
    if sq_sess and hasattr(sq_sess, 'results') and sq_sess.results is not None:
        sq_results = sq_sess.results.sort_values('Position')
        for _, row in sq_results.iterrows():
            abbr = row['Abbreviation']
            if abbr in feature_dict:
                feature_dict[abbr]['sprint_qualifying_position'] = row['Position']
        if args.debug:
            print(f'[FEATURE] SQ: sprint_qualifying_position extracted for {len(sq_results)} drivers')

    fp1_sess = loaded_sessions.get('FP1')
    if fp1_sess and hasattr(fp1_sess, 'laps'):
        try:
            fp1_laps = fp1_sess.laps.pick_quicklaps()
            fp1_best = fp1_laps.groupby('Driver')['LapTime'].min()
            fp1_best_seconds = fp1_best.dt.total_seconds()
            if not fp1_best_seconds.empty:
                fp1_fastest = fp1_best_seconds.min()
                for abbr, best_time in fp1_best_seconds.items():
                    if abbr in feature_dict:
                        feature_dict[abbr]['fp1_gap'] = best_time - fp1_fastest
                if args.debug:
                    print(f'[FEATURE] FP1: best lap times extracted for {len(fp1_best_seconds)} drivers')
        except Exception:
            pass

    # =================================================================
    # PART 4 — AUTO-EXTRACT HISTORICAL ROLLING FEATURES
    # =================================================================
    # ── Load feature store ────────────────────────────────────────────────────
    FEATURES_PATH = 'data/features/race_features.parquet'
    try:
        hist = pd.read_parquet(FEATURES_PATH)
    except Exception:
        hist = pd.DataFrame()

    if not hist.empty:
        # ── Auto-detect the driver identifier column ──────────────────────────────
        # Try common column names in priority order
        DRIVER_COL_CANDIDATES = [
            'driver_abbreviation', 'driver_code', 'abbreviation',
            'driver_id', 'driverCode', 'Driver', 'driver',
            'driver_ref', 'driverRef'
        ]

        driver_col = None
        for candidate in DRIVER_COL_CANDIDATES:
            if candidate in hist.columns:
                driver_col = candidate
                break

        if driver_col is None:
            # Last resort: find any column whose values look like driver codes
            for col in hist.columns:
                sample = hist[col].dropna().astype(str).str.upper()
                # Driver codes are 2-3 uppercase letters
                if sample.str.match(r'^[A-Z]{2,3}$').mean() > 0.5:
                    driver_col = col
                    break

        if driver_col is None:
            print("[WARN] Cannot identify driver column in feature store.")
            print(f"[WARN] Available columns: {list(hist.columns)[:20]}")
            driver_col = hist.columns[0]  # fallback to first column

        print(f"[FEATURES] Using driver column: '{driver_col}'")

        # ── Auto-detect circuit/race filter column ────────────────────────────────
        # Only use Miami rows for circuit-specific features
        CIRCUIT_COL_CANDIDATES = [
            'circuit_id', 'circuit_key', 'circuit_ref',
            'circuitId', 'EventName', 'event_name', 'location'
        ]
        circuit_col = None
        for candidate in CIRCUIT_COL_CANDIDATES:
            if candidate in hist.columns:
                circuit_col = candidate
                break

        if circuit_col:
            miami_mask = hist[circuit_col].astype(str).str.contains(
                'miami|Miami|MIAMI', na=False
            )
            hist_miami = hist[miami_mask]
            print(f"[FEATURES] Miami rows in history: {len(hist_miami)}")
        else:
            hist_miami = hist  # no circuit filter possible
            print("[WARN] No circuit column found — using all rows for circuit features")

        # ── Compute global medians for fallback ───────────────────────────────────
        ROLLING_FEATURES = [
            'rolling_avg_finish_5', 'rolling_points_5', 'circuit_win_rate',
            'circuit_avg_finish', 'dnf_rate_last_10',
            'constructor_points_standing', 'teammate_quali_delta', 'career_poles'
        ]

        # Only keep features that actually exist in the parquet
        ROLLING_FEATURES = [f for f in ROLLING_FEATURES if f in hist.columns]

        if _DEBUG_MODE:
            missing_feat = [
                f for f in [
                    'rolling_avg_finish_5','rolling_points_5','circuit_win_rate',
                    'circuit_avg_finish','dnf_rate_last_10',
                    'constructor_points_standing','teammate_quali_delta','career_poles'
                ] if f not in hist.columns
            ]
            print(f"[DEBUG] Rolling features found in parquet: {ROLLING_FEATURES}")
            print(f"[DEBUG] Rolling features NOT in parquet: {missing_feat}")

        global_medians = hist[ROLLING_FEATURES].median() if ROLLING_FEATURES else pd.Series()
    else:
        global_medians = pd.Series()
        ROLLING_FEATURES = []
        driver_col = 'driver_abbreviation'

    # ── Per-driver historical feature extraction ──────────────────────────────
    n_with_history = 0
    n_median_fills = 0

    driver_hist_cache = {}
    for abbr in drivers_df['Abbreviation']:
        if not hist.empty:
            # Normalize: try exact match first, then case-insensitive
            mask_exact = hist[driver_col].astype(str) == abbr
            mask_upper = hist[driver_col].astype(str).str.upper() == abbr.upper()

            drv_rows = hist[mask_exact] if mask_exact.any() else hist[mask_upper]

            if len(drv_rows) > 0:
                drv_rows = drv_rows.sort_values(
                    'race_date' if 'race_date' in drv_rows.columns else drv_rows.columns[0],
                    ascending=False
                )
                driver_hist_cache[abbr] = drv_rows
                n_with_history += 1
            else:
                driver_hist_cache[abbr] = pd.DataFrame()
                if _DEBUG_MODE:
                    print(f"[DEBUG] No history rows for {abbr} in column '{driver_col}'")
        else:
            driver_hist_cache[abbr] = pd.DataFrame()

    print(f"[FEATURES] Historical features loaded for {n_with_history} drivers")

    # ── Build per-driver feature dict ─────────────────────────────────────────
    def get_driver_features(abbr):
        drv_rows = driver_hist_cache.get(abbr, pd.DataFrame())
        feats = {}
        nonlocal n_median_fills

        for feat in ROLLING_FEATURES:
            if len(drv_rows) > 0 and feat in drv_rows.columns:
                val = drv_rows[feat].dropna().iloc[0] \
                      if drv_rows[feat].dropna().shape[0] > 0 else None
            else:
                val = None

            if val is None or pd.isna(val):
                val = global_medians.get(feat, 0.0)
                if _DEBUG_MODE:
                    print(f"[FILL] {abbr} {feat}: no history, using median ({val:.4f})")
                n_median_fills += 1

            feats[feat] = val

        return feats

    # Populate feature_dict
    for abbr in drivers_list:
        feats = get_driver_features(abbr)
        for k, v in feats.items():
            feature_dict[abbr][k] = v

    # =================================================================
    # PART 5 — BUILD INFERENCE DATAFRAME
    # =================================================================
    cols_file = 'reports/advanced_model_input_columns.json'
    expected_cols_race_finish = []
    expected_cols_podium = []
    expected_cols_top10 = []
    
    if os.path.exists(cols_file):
        try:
            with open(cols_file, 'r') as f:
                col_spec = json.load(f)
                expected_cols_race_finish = col_spec.get('race_finish_advanced_post_qualifying', [])
                expected_cols_podium = col_spec.get('podium_advanced_post_qualifying', [])
                expected_cols_top10 = col_spec.get('top10_advanced_post_qualifying', [])
        except:
            pass
            
    all_expected_cols = list(set(expected_cols_race_finish + expected_cols_podium + expected_cols_top10))
    
    exclude_keywords = ['target', 'finish_position', 'race_result', 'final_position', 'winner', 'podium_actual']
    all_expected_cols = [c for c in all_expected_cols if not any(k in c for k in exclude_keywords)]
    
    df_rows = []
    for abbr in drivers_list:
        row = {'driver_abbreviation': abbr}
        for col in all_expected_cols:
            row[col] = np.nan
        for k, v in feature_dict[abbr].items():
            if k in all_expected_cols or not all_expected_cols:
                row[k] = v
        df_rows.append(row)
        
    inference_df = pd.DataFrame(df_rows)
    
    cols_from_history = 0
    cols_zeroed = 0
    
    for col in inference_df.columns:
        if col == 'driver_abbreviation':
            continue
        if inference_df[col].isna().any():
            if not hist.empty and col in hist.columns and pd.api.types.is_numeric_dtype(hist[col]):
                med = hist[col].median()
                if pd.notna(med):
                    inference_df[col] = inference_df[col].fillna(med)
                    cols_from_history += 1
                else:
                    inference_df[col] = inference_df[col].fillna(0)
                    cols_zeroed += 1
            else:
                inference_df[col] = inference_df[col].fillna(0)
                cols_zeroed += 1
                
    if args.debug:
        print(f'[MATRIX] Built inference dataframe: {len(inference_df)} rows × {len(inference_df.columns)} columns')
        print(f'[MATRIX] Columns filled from FastF1: {len([c for c in inference_df.columns if c in feature_dict[drivers_list[0]]])}')
        print(f'[MATRIX] Columns filled from history: {n_with_history * len(ROLLING_FEATURES)}') # approximation
        print(f'[MATRIX] Columns filled with medians: {cols_from_history}')
        print(f'[MATRIX] Columns zeroed (no data): {cols_zeroed}')

    # =================================================================
    # PART 6 — LOAD MODELS
    # =================================================================
    MODEL_PATHS = {
        'race_finish': [
            'models/advanced/race_finish_advanced_post_qualifying.joblib',
            'models/baseline/race_finish_post_qualifying.joblib'
        ],
        'podium': [
            'models/advanced/podium_advanced_post_qualifying.joblib',
            'models/baseline/podium_post_qualifying.joblib'
        ],
        'top10': [
            'models/advanced/top10_advanced_post_qualifying.joblib',
            'models/baseline/top10_post_qualifying.joblib'
        ]
    }

    loaded_models = {}
    loaded_model_paths = {}
    for model_key, paths in MODEL_PATHS.items():
        for path in paths:
            if os.path.exists(path):
                loaded_models[model_key] = safe_load_model(path)
                loaded_model_paths[model_key] = path
                if args.debug:
                    print(f'[MODEL] Loaded: {path}')
                break
        if model_key not in loaded_models:
            if args.debug:
                print(f'[WARN] No model found for: {model_key}')

    if not loaded_models:
        print('[FATAL] No models available. Cannot proceed.')
        sys.exit(1)

    # =================================================================
    # PART 7 — RUN PREDICTIONS
    # =================================================================
    pred_finish = np.ones(n_drivers) * (n_drivers / 2)
    podium_proba = np.ones(n_drivers) * 0.5
    top10_proba = np.ones(n_drivers) * 0.5

    if 'race_finish' in loaded_models:
        model = loaded_models['race_finish']
        cols = pd.Index(expected_cols_race_finish) if expected_cols_race_finish else inference_df.columns.drop('driver_abbreviation', errors='ignore')
        X = inference_df[cols.intersection(inference_df.columns)].fillna(0)
        if hasattr(model, 'feature_names_in_'):
            X = X.reindex(columns=model.feature_names_in_, fill_value=0)
        try:
            pred_finish = model.predict(X)
        except Exception as e:
            if args.debug: print(f"Prediction error race_finish: {e}")

    if 'podium' in loaded_models:
        model = loaded_models['podium']
        cols = pd.Index(expected_cols_podium) if expected_cols_podium else inference_df.columns.drop('driver_abbreviation', errors='ignore')
        X = inference_df[cols.intersection(inference_df.columns)].fillna(0)
        if hasattr(model, 'feature_names_in_'):
            X = X.reindex(columns=model.feature_names_in_, fill_value=0)
        try:
            if hasattr(model, 'predict_proba'):
                podium_proba = model.predict_proba(X)[:, 1]
            else:
                podium_proba = model.predict(X).astype(float)
        except Exception as e:
            if args.debug: print(f"Prediction error podium: {e}")

    if 'top10' in loaded_models:
        model = loaded_models['top10']
        cols = pd.Index(expected_cols_top10) if expected_cols_top10 else inference_df.columns.drop('driver_abbreviation', errors='ignore')
        X = inference_df[cols.intersection(inference_df.columns)].fillna(0)
        if hasattr(model, 'feature_names_in_'):
            X = X.reindex(columns=model.feature_names_in_, fill_value=0)
        try:
            if hasattr(model, 'predict_proba'):
                top10_proba = model.predict_proba(X)[:, 1]
            else:
                top10_proba = model.predict(X).astype(float)
        except Exception as e:
            if args.debug: print(f"Prediction error top10: {e}")

    # =================================================================
    # PART 8 — ENSEMBLE SCORING
    # =================================================================
    finish_score = 1 - (pred_finish - 1) / (n_drivers - 1)
    finish_score = np.clip(finish_score, 0, 1)

    if 'qualifying_position' in inference_df.columns:
        qual_pos = inference_df['qualifying_position'].fillna(n_drivers).values
    else:
        qual_pos = np.ones(n_drivers) * (n_drivers / 2)
    qual_score = 1 - (qual_pos - 1) / (n_drivers - 1)
    qual_score = np.clip(qual_score, 0, 1)

    if 'podium' not in loaded_models:
        podium_proba = finish_score

    final_score = (0.50 * podium_proba) + (0.35 * finish_score) + (0.15 * qual_score)

    results_df = pd.DataFrame({
        'driver': drivers_list,
        'final_score': final_score,
        'qualifying_position': qual_pos,
        'podium_proba': podium_proba,
        'pred_finish': pred_finish,
        'finish_score': finish_score,
        'qual_score': qual_score
    })
    
    if not drivers_df.empty:
        results_df = results_df.merge(drivers_df, left_on='driver', right_on='Abbreviation', how='left')
    else:
        results_df['FullName'] = results_df['driver']
        results_df['TeamName'] = "Unknown"

    results_df = results_df.sort_values(
        by=['final_score', 'qualifying_position', 'podium_proba', 'pred_finish', 'driver'],
        ascending=[False, True, False, True, True]
    ).reset_index(drop=True)
    results_df['rank'] = results_df.index + 1

    # =================================================================
    # PART 9 — CONFIDENCE SCORING
    # =================================================================
    data_score = 0
    if 'Q' in loaded_sessions:   data_score += 40
    if 'S' in loaded_sessions:   data_score += 25
    if 'SQ' in loaded_sessions:  data_score += 15
    if 'FP1' in loaded_sessions: data_score += 10
    
    hist_coverage = (n_with_history / n_drivers) * 10 if n_drivers > 0 else 0
    data_score += hist_coverage

    if data_score >= 80:   confidence = 'High'
    elif data_score >= 55: confidence = 'Medium-High'
    elif data_score >= 35: confidence = 'Medium'
    else:                  confidence = 'Low'

    if args.debug:
        print(f"[CONFIDENCE] Data score: {data_score:.1f}/100")
        print(f"[CONFIDENCE] Level: {confidence}")

    # =================================================================
    # PART 10 — TERMINAL OUTPUT
    # =================================================================
    now_iso = datetime.datetime.now().isoformat()
    top3 = results_df.head(3)

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  GRID ORACLE — 2026 MIAMI GP MODEL PREDICTION")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    for idx, row in top3.iterrows():
        print(f"  P{int(row['rank'])}  {row['driver']:<3}  —  {row['FullName']}")

    print(f"\n  Stage:        {args.stage}")
    print(f"  Sessions:     {', '.join(loaded_sessions.keys()) if loaded_sessions else 'None'}")
    print(f"  Models:       {', '.join(loaded_models.keys())}")
    print(f"  Confidence:   {confidence}")
    print(f"  Timestamp:    {now_iso}\n")
    
    print("  ⚠  Grid Oracle models were trained on 2018–2024 data.")
    print("     This is an inference run on 2026 weekend inputs.")
    print("     Predictions reflect historical patterns only.\n")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # =================================================================
    # PART 11 — DEBUG OUTPUT
    # =================================================================
    if args.debug:
        print("\n[DEBUG] Sessions loaded:   " + (", ".join(loaded_sessions.keys()) if loaded_sessions else "None"))
        print("[DEBUG] Sessions failed:   " + (json.dumps(failed_sessions) if failed_sessions else "None"))
        print("[DEBUG] Models loaded:     " + json.dumps(list(loaded_model_paths.values()), indent=2))
        print(f"[DEBUG] Input columns:     {len(all_expected_cols)}")
        
        fastf1_cols = [c for c in inference_df.columns if c in ['qualifying_position', 'gap_to_pole_seconds', 'sprint_finish_position', 'sprint_qualifying_position', 'fp1_gap']]
        hist_cols = [c for c in inference_df.columns if c in hist_columns]
        print(f"[DEBUG] FastF1 columns:    {len(fastf1_cols)}")
        print(f"[DEBUG] History columns:   {len(hist_cols)}")
        print(f"[DEBUG] Median fills:      {cols_from_history}")
        print(f"[DEBUG] Zero fills:        {cols_zeroed}\n")
        
        print("Inference dataframe first 5 rows (selected columns):")
        cols_to_show = ['driver_abbreviation']
        for c in ['qualifying_position', 'sprint_finish_position', 'rolling_avg_finish_5']:
            if c in inference_df.columns:
                cols_to_show.append(c)
        debug_df = inference_df[cols_to_show].head().copy()
        
        debug_scores = results_df[['driver', 'podium_proba', 'finish_score']].head()
        debug_df = pd.merge(debug_df, debug_scores, left_on='driver_abbreviation', right_on='driver', how='left').drop(columns=['driver'])
        print(debug_df.to_string(index=False))
        
        print("\nFull scoring table (all drivers, sorted by final_score desc):")
        full_debug = results_df[['rank', 'driver', 'qualifying_position', 'podium_proba', 'finish_score', 'qual_score', 'final_score']]
        full_debug.columns = ['Rank', 'Driver', 'Qual', 'PodiumProb', 'FinishScore', 'QualScore', 'Final']
        print(full_debug.to_string(index=False))

    # =================================================================
    # PART 12 — SAVE OUTPUT TO JSON
    # =================================================================
    os.makedirs('reports', exist_ok=True)
    json_path = 'reports/miami_2026_model_prediction.json'
    
    top3_json = []
    for _, row in top3.iterrows():
        top3_json.append({
            "position": int(row['rank']),
            "driver": row['driver'],
            "full_name": row['FullName'],
            "team": row['TeamName'],
            "podium_probability": float(row['podium_proba']),
            "predicted_finish": float(row['pred_finish']),
            "qualifying_position": int(row['qualifying_position']) if pd.notnull(row['qualifying_position']) else None,
            "final_score": float(row['final_score'])
        })
        
    full_table_json = []
    for _, row in results_df.iterrows():
        full_table_json.append({
            "rank": int(row['rank']),
            "driver": row['driver'],
            "podium_prob": float(row['podium_proba']),
            "finish_score": float(row['finish_score']),
            "qual_score": float(row['qual_score']),
            "final_score": float(row['final_score'])
        })

    out_data = {
        "event": {
            "season": 2026,
            "round": ROUND,
            "name": EVENT_NAME,
            "stage": args.stage,
            "timestamp": now_iso
        },
        "top3": top3_json,
        "full_table": full_table_json,
        "sessions_loaded": list(loaded_sessions.keys()),
        "sessions_failed": failed_sessions,
        "models_loaded": loaded_model_paths,
        "confidence": confidence,
        "data_score": float(data_score),
        "warnings": [],
        "disclaimer": "Grid Oracle inference on 2026 inputs using 2018-2024 trained models."
    }

    with open(json_path, 'w') as f:
        json.dump(out_data, f, indent=2)

if __name__ == "__main__":
    main()
