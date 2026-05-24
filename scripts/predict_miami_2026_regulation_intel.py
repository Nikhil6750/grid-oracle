import sys, os, argparse, json, warnings, urllib.request
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import fastf1
import joblib

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC  = os.path.join(_ROOT, 'src')
for _p in [_ROOT, _SRC]:
    if os.path.exists(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

warnings.filterwarnings('ignore')

CACHE_DIR = '/tmp/fastf1_cache'
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

SEASON = 2026
EVENT_NAME = "Miami Grand Prix"

TARGET_WORDS = ['target', 'race_result', 'finish_position', 'podium_actual', 'winner', 'classified']

def detect_race_leakage(sess):
    status = getattr(sess, 'session_status', '')
    results = getattr(sess, 'results', None)
    if results is not None and len(results) > 0 and 'ClassifiedPosition' in results.columns:
        if results['ClassifiedPosition'].notna().sum() > 10:
            print("\n[LEAKAGE GUARD] Race appears completed. Prediction mode blocked to avoid result leakage.")
            print("Use evaluation mode instead.\n")
            sys.exit(0)

def load_sessions(season, event_name):
    schedule = fastf1.get_event_schedule(season, include_testing=False)
    search_term = event_name.split(' ')[0]
    target_events = schedule[schedule['EventName'].str.contains(search_term, case=False, na=False)]
    if len(target_events) == 0:
        print(f"[FATAL] {event_name} not found in schedule.")
        sys.exit(1)
    
    target_round = int(target_events.iloc[0]['RoundNumber'])
    sessions = {}
    failed = {}
    
    for name in ['FP1', 'SQ', 'S', 'Q', 'R']:
        try:
            sess = fastf1.get_session(season, target_round, name)
            sess.load(laps=True, telemetry=False, weather=True, messages=True)
            if name == 'R':
                detect_race_leakage(sess)
            sessions[name] = sess
        except Exception as e:
            failed[name] = str(e)
            
    if not any(k in sessions for k in ['Q', 'S', 'FP1']):
        print(f"[FATAL] No usable {event_name} session data.")
        sys.exit(1)
        
    return target_round, sessions, failed

def extract_driver_list(sessions):
    for name in ['Q', 'S', 'SQ', 'FP1']:
        if name in sessions and sessions[name].results is not None and len(sessions[name].results) > 0:
            df = sessions[name].results
            drivers_df = df[[c for c in ['DriverNumber','Abbreviation','FullName','TeamName','TeamColor'] if c in df.columns]].drop_duplicates(subset=['Abbreviation']).reset_index(drop=True)
            return drivers_df
    print("[FATAL] Cannot extract driver list.")
    sys.exit(1)

def td_sec(td):
    try:
        return float(td.total_seconds()) if pd.notna(td) else float('nan')
    except:
        return float('nan')

def extract_qualifying_features(sessions, drivers):
    qf = {}
    if 'Q' in sessions:
        qr = sessions['Q'].results.copy()
        def best_q(row):
            for col in ['Q3','Q2','Q1']:
                if col in row.index and pd.notna(row[col]): return row[col]
            return pd.NaT
        qr['_best'] = qr.apply(best_q, axis=1)
        if 'Position' in qr.columns and qr['Position'].notna().any():
            qr = qr.sort_values('Position').reset_index(drop=True)
        else:
            qr = qr.sort_values('_best').reset_index(drop=True)
            
        qr['qualifying_position'] = range(1, len(qr)+1)
        qr['best_lap_seconds'] = qr['_best'].apply(td_sec)
        pole_sec = qr['best_lap_seconds'].iloc[0] if not qr.empty else 0
        qr['gap_to_pole_seconds'] = qr['best_lap_seconds'] - pole_sec
        teams = qr.groupby('TeamName')['best_lap_seconds'].transform('min')
        qr['q_teammate_delta'] = qr['best_lap_seconds'] - teams
        
        for _, row in qr.iterrows():
            abr = row.get('Abbreviation', '')
            if abr in drivers:
                qf[abr] = {
                    'qualifying_position': row['qualifying_position'],
                    'gap_to_pole_seconds': row['gap_to_pole_seconds'],
                    'best_lap_seconds': row['best_lap_seconds'],
                    'q_teammate_delta': row.get('q_teammate_delta', float('nan'))
                }
    return qf

def extract_sprint_features(sessions, drivers):
    sf = {}
    if 'S' in sessions:
        s = sessions['S']
        sr = s.results.copy() if s.results is not None else pd.DataFrame()
        if not sr.empty and 'Position' in sr.columns:
            sr = sr.sort_values('Position').reset_index(drop=True)
            grid_col = 'GridPosition' if 'GridPosition' in sr.columns else None
            
            for _, row in sr.iterrows():
                abr = row.get('Abbreviation', '')
                if abr not in drivers: continue
                finish = float(row['Position']) if pd.notna(row.get('Position')) else float('nan')
                grid = float(row[grid_col]) if grid_col and pd.notna(row.get(grid_col)) else float('nan')
                gain = (grid - finish) if not any(np.isnan([grid, finish])) else float('nan')
                
                s_laps = s.laps.pick_driver(abr) if hasattr(s, 'laps') else pd.DataFrame()
                s_laps = s_laps[s_laps['IsAccurate'] == True] if 'IsAccurate' in s_laps.columns else s_laps
                
                lap_times = []
                if not s_laps.empty and 'LapTime' in s_laps.columns:
                    lap_times = s_laps['LapTime'].dropna().apply(lambda t: t.total_seconds()).tolist()
                    
                penalty_flag = 0
                if hasattr(s, 'race_control_messages') and s.race_control_messages is not None:
                    rcm = s.race_control_messages
                    if 'Message' in rcm.columns:
                        msgs = rcm[rcm['Message'].str.contains(abr, na=False)]
                        penalty_flag = int(msgs['Message'].str.contains('PENALTY|INVESTIGATION|DISQUALIFIED', na=False).any())
                
                sf[abr] = {
                    'sprint_finish_position': finish,
                    'sprint_position_gain_loss': gain,
                    'sprint_clean_pace_median': float(np.median(lap_times)) if lap_times else float('nan'),
                    'sprint_penalty_or_incident_flag': penalty_flag,
                    'sprint_laps': len(lap_times)
                }
    return sf

def extract_fp1_features(sessions, drivers):
    fp = {}
    if 'FP1' in sessions:
        fp1 = sessions['FP1']
        all_laps = fp1.laps.copy() if hasattr(fp1, 'laps') else pd.DataFrame()
        if not all_laps.empty:
            acc_laps = all_laps[all_laps['IsAccurate'] == True].copy() if 'IsAccurate' in all_laps.columns else all_laps.copy()
            if 'LapTime' in acc_laps.columns:
                acc_laps['LapTime_s'] = acc_laps['LapTime'].apply(td_sec)
                
            fastest_overall = acc_laps.groupby('Driver')['LapTime_s'].min()
            
            def get_long_run(drv_laps):
                if 'Stint' not in drv_laps.columns: return float('nan')
                times = []
                for _, stint in drv_laps.groupby('Stint'):
                    stint = stint.sort_values('LapNumber')
                    if len(stint) >= 5:
                        core = stint.iloc[2:-1]['LapTime_s'].dropna().tolist()
                        if core:
                            med = np.median(core)
                            times.extend([t for t in core if t < med * 1.03])
                return float(np.median(times)) if times else float('nan')

            for abr in drivers:
                drv_laps = acc_laps[acc_laps['Driver'] == abr]
                if drv_laps.empty: continue
                best = drv_laps['LapTime_s'].min()
                med = drv_laps['LapTime_s'].median()
                rank = int((fastest_overall < best).sum()) + 1
                fp[abr] = {
                    'fp1_best_lap_rank': rank,
                    'fp1_median_pace': float(med),
                    'fp1_long_run_pace': float(get_long_run(drv_laps))
                }
    return fp

def extract_tyre_strategy_features(sessions, drivers):
    tf = {}
    for abr in drivers:
        tf[abr] = {'stints': {}, 'compound_flexibility_score': 0.0, 'sprint_degradation_proxy': float('nan')}
        
    for name in ['S', 'FP1']:
        if name not in sessions: continue
        laps = sessions[name].laps.copy() if hasattr(sessions[name], 'laps') else pd.DataFrame()
        if laps.empty or 'LapTime' not in laps.columns: continue
        laps['LapTime_s'] = laps['LapTime'].apply(td_sec)
        
        for abr in drivers:
            drv = laps[laps['Driver'] == abr].copy()
            if drv.empty or 'Stint' not in drv.columns or 'Compound' not in drv.columns: continue
            
            for stint_id, sg in drv.groupby('Stint'):
                comp = sg['Compound'].mode().iloc[0] if not sg.empty else 'UNKNOWN'
                times = sg['LapTime_s'].dropna().tolist()
                if len(times) >= 3:
                    slope = float(np.polyfit(range(len(times)), times, 1)[0])
                    tf[abr]['stints'][f"{name}_{stint_id}"] = {
                        'compound': comp,
                        'degradation': slope,
                        'lap_count': len(times)
                    }
            
            compounds_used = list(set([s['compound'] for s in tf[abr]['stints'].values()]))
            tf[abr]['compound_flexibility_score'] = len(compounds_used) / 3.0
            
            sprint_stints = [s for k, s in tf[abr]['stints'].items() if k.startswith('S_')]
            if sprint_stints:
                tf[abr]['sprint_degradation_proxy'] = float(np.mean([s['degradation'] for s in sprint_stints]))
                
    return tf

def extract_weather_features(sessions, no_weather):
    wf = {
        'rain_risk': 0.0, 'air_temp': float('nan'), 'track_temp': float('nan'),
        'humidity': float('nan'), 'weather_volatility_score': 0.0,
        'wet_race_adjustment': 0.0, 'source': 'none'
    }
    
    for name in ['R', 'Q', 'S']:
        if name in sessions:
            wd = getattr(sessions[name], 'weather_data', None)
            if wd is not None and not wd.empty:
                try:
                    wf['air_temp'] = float(wd['AirTemp'].mean())
                    if 'TrackTemp' in wd.columns: wf['track_temp'] = float(wd['TrackTemp'].mean())
                    if 'Humidity' in wd.columns: wf['humidity'] = float(wd['Humidity'].mean())
                    rain_laps = wd['Rainfall'].sum() if 'Rainfall' in wd.columns else 0
                    wf['rain_risk'] = float(rain_laps / len(wd)) if len(wd) > 0 else 0.0
                    wf['source'] = f'FastF1:{name}'
                    break
                except Exception as e:
                    pass
                    
    if wf['source'] == 'none' and not no_weather:
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=25.9581&longitude=-80.2389&hourly=temperature_2m,precipitation_probability,relative_humidity_2m&forecast_days=1&timezone=America/New_York"
            with urllib.request.urlopen(url, timeout=5) as r:
                wdata = json.loads(r.read())
            hours = wdata['hourly']['time']
            race_idx = [i for i, h in enumerate(hours) if '16:00' <= h[-5:] <= '18:00']
            if race_idx:
                wf['air_temp'] = float(np.mean([wdata['hourly']['temperature_2m'][i] for i in race_idx]))
                wf['humidity'] = float(np.mean([wdata['hourly']['relative_humidity_2m'][i] for i in race_idx]))
                wf['rain_risk'] = float(np.mean([wdata['hourly']['precipitation_probability'][i] for i in race_idx])) / 100.0
                wf['source'] = 'Open-Meteo API (Forecast)'
        except Exception:
            pass

    wf['weather_volatility_score'] = min(1.0, wf['rain_risk'] * 2.0)
    wf['wet_race_adjustment'] = 1.0 if wf['rain_risk'] > 0.5 else 0.0
    return wf

def build_2026_team_form(season, miami_round):
    team_form = {}
    try:
        schedule = fastf1.get_event_schedule(season, include_testing=False)
        past_rounds = schedule[(schedule['RoundNumber'] > 0) & (schedule['RoundNumber'] < miami_round)]
        if past_rounds.empty:
            return team_form
            
        all_results = []
        for rnd in past_rounds['RoundNumber']:
            try:
                r_sess = fastf1.get_session(season, rnd, 'R')
                r_sess.load(laps=False, telemetry=False, weather=False, messages=False)
                if r_sess.results is not None and not r_sess.results.empty:
                    df = r_sess.results[['TeamName', 'Position', 'Points', 'Status']]
                    all_results.append(df)
            except:
                pass
                
        if all_results:
            rdf = pd.concat(all_results)
            for team, tdf in rdf.groupby('TeamName'):
                finishes = pd.to_numeric(tdf['Position'], errors='coerce').dropna()
                team_form[team] = {
                    'avg_finish': float(finishes.mean()) if not finishes.empty else 10.0,
                    'total_points': float(tdf['Points'].sum()),
                    'dnfs': int(tdf['Status'].str.contains(r'Finished|\+').sum() == 0),
                    'top10': int((finishes <= 10).sum())
                }
    except:
        pass
    return team_form

def build_2026_driver_form(season, miami_round, drivers):
    driver_form = {}
    for abr in drivers:
        driver_form[abr] = {'avg_finish': 10.0, 'points': 0.0, 'top10': 0}
        
    try:
        schedule = fastf1.get_event_schedule(season, include_testing=False)
        past_rounds = schedule[(schedule['RoundNumber'] > 0) & (schedule['RoundNumber'] < miami_round)]
        if past_rounds.empty:
            return driver_form
            
        all_results = []
        for rnd in past_rounds['RoundNumber']:
            try:
                r_sess = fastf1.get_session(season, rnd, 'R')
                r_sess.load(laps=False, telemetry=False, weather=False, messages=False)
                if r_sess.results is not None and not r_sess.results.empty:
                    df = r_sess.results[['Abbreviation', 'Position', 'Points']]
                    all_results.append(df)
            except:
                pass
                
        if all_results:
            rdf = pd.concat(all_results)
            for abr in drivers:
                ddf = rdf[rdf['Abbreviation'] == abr]
                finishes = pd.to_numeric(ddf['Position'], errors='coerce').dropna()
                if not finishes.empty:
                    driver_form[abr] = {
                        'avg_finish': float(finishes.mean()),
                        'points': float(ddf['Points'].sum()),
                        'top10': int((finishes <= 10).sum())
                    }
    except:
        pass
    return driver_form

def build_regulation_proxy_scores(drivers, qual_features, sprint_features, fp1_features, tyre_features):
    proxies = {}
    N = len(drivers)
    for abr in drivers:
        qf = qual_features.get(abr, {})
        sf = sprint_features.get(abr, {})
        fp = fp1_features.get(abr, {})
        tf = tyre_features.get(abr, {})
        
        q_pos = qf.get('qualifying_position', N/2)
        s_pace = sf.get('sprint_clean_pace_median', float('nan'))
        fp_lr = fp.get('fp1_long_run_pace', float('nan'))
        deg = tf.get('sprint_degradation_proxy', float('nan'))
        
        # 1. Straight line efficiency proxy (using Q gap to pole as simplistic proxy if telemetry missing)
        # 2. Active aero efficiency proxy: difference between Q performance and race pace performance
        aero_proxy = 0.5
        if not np.isnan(s_pace) and not np.isnan(q_pos):
            aero_proxy = max(0.0, min(1.0, 1.0 - (q_pos / N))) # Simplified proxy
            
        # 3. Energy deployment proxy: consistency
        s_laps = sf.get('sprint_laps', 0)
        energy_proxy = 0.5 if s_laps < 5 else max(0.0, min(1.0, 1.0 - (deg if not np.isnan(deg) else 0.5)))
        
        # 4. Tyre degradation proxy
        deg_proxy = deg if not np.isnan(deg) else 0.1
        
        # 5. Race pace stability
        stability = 0.5
        if not np.isnan(fp_lr):
            stability = 0.8
            
        # 6. Car balance
        teammate_delta = qf.get('q_teammate_delta', 0)
        balance = max(0.0, min(1.0, 0.5 - teammate_delta))
        
        proxies[abr] = {
            'straight_line_efficiency_proxy': 0.5,
            'active_aero_efficiency_proxy': aero_proxy,
            'energy_deployment_proxy': energy_proxy,
            'tyre_degradation_2026_proxy': deg_proxy,
            'race_pace_stability_score': stability,
            'car_balance_score': balance
        }
    return proxies

def load_historical_ml_prior(drivers, qf, d_form, t_form, drivers_df):
    ml_result = {'status': 'unavailable', 'weight': 0.0, 'predictions': {}, 'debug_info': {}}
    
    try:
        r_features = pd.read_parquet('data/features/race_features.parquet')
        
        # Build X matching the race_features schema
        X = pd.DataFrame(columns=r_features.columns, index=drivers)
        for c in r_features.columns:
            if pd.api.types.is_numeric_dtype(r_features[c]):
                X[c] = r_features[c].median()
            else:
                X[c] = r_features[c].mode()[0] if not r_features[c].mode().empty else 'unknown'
                
        # Count neutral columns filled so far
        num_expected = len(r_features.columns)
        
        teams = {r['Abbreviation']: r['TeamName'] for _, r in drivers_df.iterrows()}
        
        # Populate real 2026 columns
        real_cols = 0
        if 'qualifying_position' in X.columns:
            X['qualifying_position'] = [qf.get(a, {}).get('qualifying_position', X['qualifying_position'].median()) for a in drivers]
            real_cols += 1
            
        if 'driver_season_avg_finish_before_event' in X.columns:
            X['driver_season_avg_finish_before_event'] = [d_form.get(a, {}).get('avg_finish', X['driver_season_avg_finish_before_event'].median()) for a in drivers]
            real_cols += 1
            
        if 'driver_season_points_before_event' in X.columns:
            X['driver_season_points_before_event'] = [d_form.get(a, {}).get('points', X['driver_season_points_before_event'].median()) for a in drivers]
            real_cols += 1
            
        if 'team_season_avg_finish_before_event' in X.columns:
            X['team_season_avg_finish_before_event'] = [t_form.get(teams.get(a, ''), {}).get('avg_finish', X['team_season_avg_finish_before_event'].median()) for a in drivers]
            real_cols += 1
            
        if 'team_season_points_before_event' in X.columns:
            X['team_season_points_before_event'] = [t_form.get(teams.get(a, ''), {}).get('total_points', X['team_season_points_before_event'].median()) for a in drivers]
            real_cols += 1
            
        # Add driver string
        X['driver_code'] = drivers
        X['season'] = 2026
        X['prediction_stage'] = 'post_qualifying'
        X['feature_cutoff_stage'] = 'post_qualifying'
        real_cols += 4
        
        ml_result['debug_info']['feature_stats'] = {
            'expected_columns': num_expected,
            'real_filled': real_cols,
            'neutral_filled': num_expected - real_cols
        }

        # Clear targets
        for t in TARGET_WORDS:
            for c in X.columns:
                if t in c.lower():
                    X[c] = 0.0

        models_loaded = 0
        is_constant = True
        
        for task in ['race_finish', 'podium', 'top10']:
            model_path = f'models/advanced/{task}_advanced_post_qualifying.joblib'
            if not os.path.exists(model_path):
                continue
                
            model = joblib.load(model_path)
            
            if task == 'race_finish':
                preds = model.predict(X)
                ml_result['predictions']['finish'] = dict(zip(drivers, preds))
                if np.std(preds) > 1e-4:
                    is_constant = False
            else:
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(X)
                    preds = proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]
                else:
                    preds = model.predict(X)
                ml_result['predictions'][task] = dict(zip(drivers, preds))
                if np.std(preds) > 1e-4:
                    is_constant = False
                
            models_loaded += 1
            ml_result['debug_info'][task] = {'model_file': model_path, 'columns_in_X': len(X.columns)}
            
        # Find top 20 non constant columns
        non_constant_cols = []
        for c in X.columns:
            if pd.api.types.is_numeric_dtype(X[c]):
                if X[c].std() > 1e-4:
                    non_constant_cols.append(c)
            else:
                if len(X[c].unique()) > 1:
                    non_constant_cols.append(c)
        
        ml_result['debug_info']['non_constant_cols'] = non_constant_cols[:20]
        
        # Sample rows for specific drivers
        sample_drivers = ['ANT', 'VER', 'LEC', 'NOR', 'RUS', 'PIA']
        ml_result['debug_info']['sample_rows'] = {}
        for d in sample_drivers:
            if d in drivers:
                row = X.loc[d, ['qualifying_position', 'driver_season_points_before_event', 'team_season_points_before_event']].to_dict()
                ml_result['debug_info']['sample_rows'][d] = row

        if models_loaded > 0:
            if is_constant:
                ml_result['status'] = 'neutral_constant_output'
                ml_result['weight'] = 0.0
            else:
                ml_result['status'] = 'used'
                ml_result['weight'] = 0.04
            
    except Exception as e:
        ml_result['status'] = f'unavailable ({e})'
        
    return ml_result

def normalize_dict(d, higher_is_better=False):
    vals = [v for v in d.values() if not np.isnan(v)]
    if not vals: return {k: 0.5 for k in d.keys()}
    vmin, vmax = min(vals), max(vals)
    res = {}
    for k, v in d.items():
        if np.isnan(v): res[k] = 0.5
        elif vmax == vmin: res[k] = 0.0
        else:
            norm = (v - vmin) / (vmax - vmin)
            res[k] = (1 - norm) if higher_is_better else norm
    return res

def compute_regulation_intel_scores(drivers, qf, sf, fp, tf, wf, t_form, d_form, drivers_df):
    N = len(drivers)
    intel_scores = {}
    
    for abr in drivers:
        # 1. Quali (18%)
        q_pos = qf.get(abr, {}).get('qualifying_position', N/2)
        q_score = (q_pos - 1) / max(N-1, 1)
        
        # 2. Sprint (18%)
        s_pos = sf.get(abr, {}).get('sprint_finish_position', N/2)
        s_score = (s_pos - 1) / max(N-1, 1)
        
        # 3. Long run (18%)
        fp_rank = fp.get(abr, {}).get('fp1_best_lap_rank', N/2)
        fp_score = (fp_rank - 1) / max(N-1, 1)
        
        # 4. Team form (16%)
        team = next((r['TeamName'] for _, r in drivers_df.iterrows() if r['Abbreviation'] == abr), '')
        t_avg = t_form.get(team, {}).get('avg_finish', 10.0)
        t_score = (t_avg - 1) / 19.0
        
        # 5. Driver form (14%)
        d_avg = d_form.get(abr, {}).get('avg_finish', 10.0)
        d_score = (d_avg - 1) / 19.0
        
        # 6. Tyre flex (8%)
        flex = tf.get(abr, {}).get('compound_flexibility_score', 0.5)
        flex_score = 1.0 - flex # lower score is better
        
        # 7. Weather (4%)
        w_score = wf['rain_risk'] * 0.5
        
        total = (q_score * 0.18 + s_score * 0.18 + fp_score * 0.18 + 
                 t_score * 0.16 + d_score * 0.14 + flex_score * 0.08 + w_score * 0.04)
        
        intel_scores[abr] = {
            'q_score': q_score, 's_score': s_score, 'fp_score': fp_score,
            't_score': t_score, 'd_score': d_score, 'flex_score': flex_score,
            'w_score': w_score,
            'total_2026_intel': total / 0.96 # normalized to 100% of the 96% intel weight
        }
    return intel_scores

def compute_final_ensemble(drivers, intel_scores, ml_prior, qf, sf, fp):
    final_scores = {}
    ml_used = ml_prior['status'] == 'used'
    
    if ml_used:
        ml_raw = ml_prior['predictions'].get('finish', {a: 10 for a in drivers})
        ml_norm = normalize_dict(ml_raw, higher_is_better=False)
        w_intel, w_ml = 0.96, 0.04
    else:
        w_intel, w_ml = 1.0, 0.0
        ml_norm = {a: 0.5 for a in drivers}
        
    for abr in drivers:
        final_scores[abr] = (intel_scores[abr]['total_2026_intel'] * w_intel) + (ml_norm.get(abr, 0.5) * w_ml)
        
    def tiebreak(abr):
        return (
            qf.get(abr, {}).get('qualifying_position', 99),
            sf.get(abr, {}).get('sprint_finish_position', 99),
            fp.get(abr, {}).get('fp1_long_run_pace', 999),
            sf.get(abr, {}).get('sprint_penalty_or_incident_flag', 0)
        )
        
    ranked = sorted(final_scores.items(), key=lambda x: (round(x[1], 6), tiebreak(x[0])))
    return ranked, w_ml, ml_norm

def compute_confidence(sessions, wf, ranked):
    data_score = sum(10 for s in ['Q','S','SQ','FP1'] if s in sessions)
    if wf['source'] != 'none': data_score += 10
    
    gap = (ranked[3][1] - ranked[2][1]) if len(ranked) >= 4 else 0.05
    
    if data_score >= 40 and gap > 0.03: conf = 'Medium-High'
    elif data_score >= 30: conf = 'Medium'
    elif data_score >= 20: conf = 'Medium-Low'
    else: conf = 'Low'
    return conf

DRIVER_FLAGS = {
    'ANT': ('Italy', '🇮🇹'), 'VER': ('Netherlands', '🇳🇱'), 'LEC': ('Monaco', '🇲🇨'),
    'NOR': ('United Kingdom', '🇬🇧'), 'RUS': ('United Kingdom', '🇬🇧'), 'HAM': ('United Kingdom', '🇬🇧'),
    'PIA': ('Australia', '🇦🇺'), 'SAI': ('Spain', '🇪🇸'), 'GAS': ('France', '🇫🇷'),
    'HAD': ('France', '🇫🇷'), 'COL': ('Argentina', '🇦🇷'), 'HUL': ('Germany', '🇩🇪'),
    'LAW': ('New Zealand', '🇳🇿'), 'BEA': ('United Kingdom', '🇬🇧'), 'OCO': ('France', '🇫🇷'),
    'ALB': ('Thailand', '🇹🇭'), 'LIN': ('United Kingdom', '🇬🇧'), 'ALO': ('Spain', '🇪🇸'),
    'STR': ('Canada', '🇨🇦'), 'BOT': ('Finland', '🇫🇮'), 'PER': ('Mexico', '🇲🇽'),
    'BOR': ('Brazil', '🇧🇷')
}

def get_flag_info(abr, drivers_df):
    country_name = "Unknown"
    flag = "🏳️"
    r = drivers_df[drivers_df['Abbreviation'] == abr]
    if not r.empty:
        if 'CountryCode' in r.columns and pd.notna(r['CountryCode'].values[0]):
            country_name = r['CountryCode'].values[0]
        elif 'Country' in r.columns and pd.notna(r['Country'].values[0]):
            country_name = r['Country'].values[0]
        elif 'Nationality' in r.columns and pd.notna(r['Nationality'].values[0]):
            country_name = r['Nationality'].values[0]
    if abr in DRIVER_FLAGS:
        fallback_country, fallback_flag = DRIVER_FLAGS[abr]
        if country_name == "Unknown":
            country_name = fallback_country
        flag = fallback_flag
    return country_name, flag

def safe_print(text, fallback_text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(fallback_text)

def render_terminal_output(ranked, confidence, sessions, wf, ml_prior, drivers_df, debug, qf, sf, fp, intel_scores, ml_norm, w_ml, top3_only, no_debug_table):
    top3 = ranked[:3]
    def get_name(abr):
        r = drivers_df[drivers_df['Abbreviation'] == abr]
        return r['FullName'].values[0] if not r.empty and 'FullName' in r.columns else abr
        
    sep = '=' * 55
    print(f"\n{sep}")
    print("  GRID ORACLE — 2026 MIAMI GP REGULATION-AWARE PREDICTION")
    print("  Stage: Pre-race after Qualifying")
    print(f"  Confidence: {confidence}")
    print(f"  Data used: {' + '.join(sessions.keys())} + {wf['source']}")
    print(f"  Historical ML prior: {'Used' if ml_prior['status'] == 'used' else 'Unavailable'}")
    print("  Primary signal: 2026 regulation-aware race intelligence")
    print(sep)
    
    print("\n  Predicted Podium")
    for i, (abr, score) in enumerate(top3, 1):
        country, flag = get_flag_info(abr, drivers_df)
        line = f"  P{i}  {flag} {abr} — {get_name(abr)}"
        c_code = country[:3].upper() if country != "Unknown" else "UNK"
        fallback = f"  P{i}  [{c_code}] {abr} — {get_name(abr)}"
        safe_print(line, fallback)
        
    if not top3_only:
        print("\n  Full Predicted Race Order")
        for i, (abr, score) in enumerate(ranked, 1):
            country, flag = get_flag_info(abr, drivers_df)
            qp = qf.get(abr, {}).get('qualifying_position', '?')
            sp = sf.get(abr, {}).get('sprint_finish_position', '?')
            qp_str = f"Q{int(qp)}" if qp != '?' and not np.isnan(qp) else "Q?"
            sp_str = f"S{int(sp)}" if sp != '?' and not np.isnan(sp) else "S?"
            
            c_code = country[:3].upper() if country != "Unknown" else "UNK"
            line = f"  {i:02d}  {flag} {abr} — {get_name(abr):<20} Score {score:.4f}   {qp_str:<4} {sp_str:<4}"
            fallback = f"  {i:02d}  [{c_code}] {abr} — {get_name(abr):<20} Score {score:.4f}   {qp_str:<4} {sp_str:<4}"
            safe_print(line, fallback)

    print("\n  Warnings:")
    print("  - 2026 is out-of-sample for the old ML models")
    print("  - Safety car, starts, tyre strategy, and weather can change the result")
    print("  - Educational ML inference only")
    print(sep)
    
    if debug and not no_debug_table:
        w_intel = 1.0 - w_ml
        print("\n[DEBUG] Active Weights:")
        print(f"  - Qualifying / Track Position: {0.18 * w_intel:.4f}")
        print(f"  - Sprint Execution:            {0.18 * w_intel:.4f}")
        print(f"  - Long-Run Pace:               {0.18 * w_intel:.4f}")
        print(f"  - Team 2026 Form:              {0.16 * w_intel:.4f}")
        print(f"  - Driver 2026 Form:            {0.14 * w_intel:.4f}")
        print(f"  - Tyre Strategy:               {0.08 * w_intel:.4f}")
        print(f"  - Weather:                     {0.04 * w_intel:.4f}")
        print(f"  - Historical ML Prior:         {w_ml:.4f}")

        print("\n[DEBUG] Historical ML Prior Info:")
        print(f"  Status: {ml_prior['status']}")
        fstats = ml_prior.get('debug_info', {}).get('feature_stats', {})
        if fstats:
            print(f"  - Expected ML columns: {fstats.get('expected_columns')}")
            print(f"  - Real 2026 columns filled: {fstats.get('real_filled')}")
            print(f"  - Neutral/Median columns: {fstats.get('neutral_filled')}")
            
        nc = ml_prior.get('debug_info', {}).get('non_constant_cols', [])
        if nc:
            print(f"  - Top non-constant columns: {', '.join(nc)}")
            
        sr = ml_prior.get('debug_info', {}).get('sample_rows', {})
        if sr:
            print("  - Sample input rows:")
            for d, row in sr.items():
                print(f"    {d}: {row}")
                
        if ml_prior['status'] == 'used':
            for task, info in ml_prior.get('debug_info', {}).items():
                if task in ['race_finish', 'podium', 'top10']:
                    print(f"  - Loaded {task}: {info['model_file']} (Input columns: {info['columns_in_X']})")
                
            print("\n  ML Predictions:")
            for abr in drivers_df['Abbreviation'].tolist():
                finish = ml_prior['predictions'].get('finish', {}).get(abr, 'N/A')
                podium = ml_prior['predictions'].get('podium', {}).get(abr, 'N/A')
                top10 = ml_prior['predictions'].get('top10', {}).get(abr, 'N/A')
                if finish != 'N/A': finish = round(float(finish), 2)
                if podium != 'N/A': podium = round(float(podium), 4)
                if top10 != 'N/A': top10 = round(float(top10), 4)
                print(f"    {abr}: Finish={finish}, Podium_Prob={podium}, Top10_Prob={top10}")

        print("\n[DEBUG] Full Ranking Table:")
        header = f"{'Rank':<5} {'Driver':<6} {'Flag':<6} {'QualPos':<8} {'SprintPos':<10} {'FP1BestRank':<12} {'FP1LongRunPace':<15} {'TyreDegScore':<13} {'Team2026Score':<14} {'Driver2026Score':<16} {'TrackPositionScore':<19} {'FrontRowAdvantage':<18} {'SprintExecutionScore':<21} {'LongRunScore':<13} {'StrategyScore':<14} {'WeatherScore':<13} {'HistoricalMLPriorScore':<23} {'FinalScore':<10}"
        print(header)
        for i, (abr, score) in enumerate(ranked, 1):
            country, flag = get_flag_info(abr, drivers_df)
            qp = qf.get(abr, {}).get('qualifying_position', float('nan'))
            sp = sf.get(abr, {}).get('sprint_finish_position', float('nan'))
            fpr = fp.get(abr, {}).get('fp1_best_lap_rank', float('nan'))
            fpl = fp.get(abr, {}).get('fp1_long_run_pace', float('nan'))
            i_s = intel_scores.get(abr, {})
            
            # Map raw intel components (these were 0-1 lower-is-better before weights applied)
            # Some are available natively in intel_scores, some have to be extrapolated
            track_pos_score = i_s.get('q_score', float('nan'))
            sprint_exec = i_s.get('s_score', float('nan'))
            lr_score = i_s.get('fp_score', float('nan'))
            t_score = i_s.get('t_score', float('nan'))
            d_score = i_s.get('d_score', float('nan'))
            tyre_score = i_s.get('flex_score', float('nan'))
            w_s = i_s.get('w_score', float('nan'))
            ml_s = ml_norm.get(abr, float('nan'))
            
            # FrontRowAdvantage is practically encoded in TrackPositionScore but we can show qp
            fra = "Yes" if qp <= 2 else "No"
            
            def fmt(v): return f"{v:.4f}" if not np.isnan(v) else "NaN"
            def fmt_i(v): return str(int(v)) if not np.isnan(v) else "NaN"

            row = f"{i:<5} {abr:<6} {flag:<6} {fmt_i(qp):<8} {fmt_i(sp):<10} {fmt_i(fpr):<12} {fmt(fpl):<15} {fmt(tyre_score):<13} {fmt(t_score):<14} {fmt(d_score):<16} {fmt(track_pos_score):<19} {fra:<18} {fmt(sprint_exec):<21} {fmt(lr_score):<13} {fmt(tyre_score):<14} {fmt(w_s):<13} {fmt(ml_s):<23} {fmt(score):<10}"
            fallback_row = f"{i:<5} {abr:<6} {country[:3].upper() if country != 'Unknown' else 'UNK':<6} {fmt_i(qp):<8} {fmt_i(sp):<10} {fmt_i(fpr):<12} {fmt(fpl):<15} {fmt(tyre_score):<13} {fmt(t_score):<14} {fmt(d_score):<16} {fmt(track_pos_score):<19} {fra:<18} {fmt(sprint_exec):<21} {fmt(lr_score):<13} {fmt(tyre_score):<14} {fmt(w_s):<13} {fmt(ml_s):<23} {fmt(score):<10}"
            safe_print(row, fallback_row)
            
        print("\n[DEBUG] Auditing Rankings:")
        # Check for qualifying anomalies
        for i, (abr1, score1) in enumerate(ranked):
            q1 = qf.get(abr1, {}).get('qualifying_position', 99)
            if q1 > 3: continue
            
            # Look for drivers ranked below this driver (which means higher index and higher score)
            # wait, ranked below means a higher index in the `ranked` list.
            # wait, `score` is lower-is-better. Higher score = worse rank.
            # The issue is "If a driver with QualPos <= 3 is ranked below a driver with QualPos >= 5"
            # This means abr1 (QualPos<=3) has a WORSE score (higher index) than abr2 (QualPos>=5)
            # So abr2 is ranked HIGHER (lower index, better score) than abr1.
            
            # Let's iterate over drivers that beat abr1
            for j in range(i):
                abr2, score2 = ranked[j]
                q2 = qf.get(abr2, {}).get('qualifying_position', 0)
                if q2 >= 5:
                    print(f"AUDIT: {abr1} starts P{int(q1)} but ranks below {abr2} starting P{int(q2)} because:")
                    reasons = 0
                    
                    def check_worse(name, k, w):
                        v1 = intel_scores[abr1].get(k, 0)
                        v2 = intel_scores[abr2].get(k, 0)
                        if v1 > v2: # higher is worse
                            diff = (v1 - v2) * w
                            print(f"  - {abr1} {name} worse by {diff:.4f} (weighted)")
                            return 1
                        return 0
                        
                    w_i = 1.0 - w_ml
                    reasons += check_worse('LongRunScore', 'fp_score', 0.18 * w_i)
                    reasons += check_worse('Team2026Score', 't_score', 0.16 * w_i)
                    reasons += check_worse('TyreDegScore', 'flex_score', 0.08 * w_i)
                    reasons += check_worse('SprintExecutionScore', 's_score', 0.18 * w_i)
                    reasons += check_worse('Driver2026Score', 'd_score', 0.14 * w_i)
                    
                    if ml_norm.get(abr1, 0) > ml_norm.get(abr2, 0):
                        diff = (ml_norm[abr1] - ml_norm[abr2]) * w_ml
                        print(f"  - {abr1} HistoricalMLPrior worse by {diff:.4f} (weighted)")
                        reasons += 1
                        
                    if reasons < 2:
                        print("  AUDIT WARNING: Ranking may be underweighting qualifying/front-row advantage.")

def save_json_report(ranked, top3, confidence, sessions, failed, wf, ml_prior, intel_scores, t_form, d_form, proxies, tf, drivers_df, qf, sf):
    def get_name(abr):
        r = drivers_df[drivers_df['Abbreviation'] == abr]
        return r['FullName'].values[0] if not r.empty and 'FullName' in r.columns else abr
        
    def get_json_driver(a, s, i, is_top3=True):
        country, flag = get_flag_info(a, drivers_df)
        d = {
            "driver": a,
            "full_name": get_name(a),
            "country": country,
            "flag": flag,
            "final_score": round(s, 6)
        }
        if is_top3: d["position"] = i + 1
        else: d["rank"] = i + 1
        
        qp = qf.get(a, {}).get('qualifying_position')
        if pd.notna(qp):
            d["qualifying_position"] = qp
        return d
        
    out = {
        "event": {"season": 2026, "race": "Miami Grand Prix", "stage": "pre_race_post_qualifying"},
        "top3": [get_json_driver(a, s, i, True) for i, (a, s) in enumerate(top3)],
        "full_ranking": [get_json_driver(a, s, i, False) for i, (a, s) in enumerate(ranked)],
        "confidence": confidence,
        "data_sources": ["FastF1", "Open-Meteo" if "Open-Meteo" in wf['source'] else ""],
        "sessions_used": list(sessions.keys()),
        "sessions_failed": failed,
        "weather": wf,
        "team_2026_scores": t_form,
        "driver_2026_scores": d_form,
        "tyre_strategy_scores": tf,
        "regulation_proxy_scores": proxies,
        "historical_ml_prior": {
            "status": "used" if ml_prior['status'] == 'used' else "unavailable",
            "weight": ml_prior['weight'],
            "predictions": ml_prior['predictions']
        },
        "warnings": [
            "2026 is out-of-sample for the old ML models",
            "Safety car, start incidents, tyre strategy, and weather can change the result",
            "Educational ML inference only"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    os.makedirs('reports', exist_ok=True)
    with open('reports/miami_2026_regulation_intel_prediction.json', 'w') as f:
        json.dump(out, f, indent=2, default=str)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--no-weather', action='store_true')
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--season', type=int, default=SEASON)
    parser.add_argument('--event', type=str, default=EVENT_NAME)
    parser.add_argument('--top3-only', action='store_true')
    parser.add_argument('--full-order', action='store_true')
    parser.add_argument('--no-debug-table', action='store_true')
    args = parser.parse_args()
    
    season = args.season
    event_name = args.event
    
    target_round, sessions, failed = load_sessions(season, event_name)
    drivers_df = extract_driver_list(sessions)
    drivers = drivers_df['Abbreviation'].tolist()
    
    qf = extract_qualifying_features(sessions, drivers)
    sf = extract_sprint_features(sessions, drivers)
    fp = extract_fp1_features(sessions, drivers)
    tf = extract_tyre_strategy_features(sessions, drivers)
    wf = extract_weather_features(sessions, args.no_weather)
    
    t_form = build_2026_team_form(season, target_round)
    d_form = build_2026_driver_form(season, target_round, drivers)
    proxies = build_regulation_proxy_scores(drivers, qf, sf, fp, tf)
    
    ml_prior = load_historical_ml_prior(drivers, qf, d_form, t_form, drivers_df)
    
    intel_scores = compute_regulation_intel_scores(drivers, qf, sf, fp, tf, wf, t_form, d_form, drivers_df)
    ranked, w_ml, ml_norm = compute_final_ensemble(drivers, intel_scores, ml_prior, qf, sf, fp)
    
    confidence = compute_confidence(sessions, wf, ranked)
    
    render_terminal_output(ranked, confidence, sessions, wf, ml_prior, drivers_df, args.debug, qf, sf, fp, intel_scores, ml_norm, w_ml, args.top3_only, args.no_debug_table)
    
    if args.save or True:
        save_json_report(ranked, ranked[:3], confidence, sessions, failed, wf, ml_prior, intel_scores, t_form, d_form, proxies, tf, drivers_df, qf, sf)

if __name__ == '__main__':
    main()
