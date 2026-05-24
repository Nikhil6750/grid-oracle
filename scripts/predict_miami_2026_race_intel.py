import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC  = os.path.join(_ROOT, 'src')
for _p in [_ROOT, _SRC]:
    if os.path.exists(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import argparse, json, warnings, traceback
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import fastf1
import joblib

warnings.filterwarnings('ignore')
CACHE_DIR = '/tmp/fastf1_cache'
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

SEASON = 2026

# Auto-discover Miami round number
schedule = fastf1.get_event_schedule(SEASON, include_testing=False)
miami = schedule[
    schedule['EventName'].str.contains('Miami', case=False, na=False)
].iloc[0]
ROUND = int(miami['RoundNumber'])

SESSIONS_TO_LOAD = ['FP1', 'SQ', 'S', 'Q', 'R']
loaded  = {}
failed  = {}

for name in SESSIONS_TO_LOAD:
    try:
        sess = fastf1.get_session(SEASON, ROUND, name)
        sess.load(
            laps=True,
            telemetry=False,
            weather=True,
            messages=True
        )
        # LEAKAGE GUARD: block race result if R session is complete
        if name == 'R':
            status = getattr(sess, 'session_status', '')
            results = getattr(sess, 'results', None)
            race_finished = (
                results is not None and
                len(results) > 0 and
                'ClassifiedPosition' in results.columns and
                results['ClassifiedPosition'].notna().sum() > 10
            )
            if race_finished:
                print(
                    "\n[LEAKAGE GUARD] Race appears completed. "
                    "Prediction mode blocked to avoid result leakage.\n"
                    "Use evaluation mode instead.\n"
                )
                sys.exit(0)
            else:
                print(f"[SESSION] R session exists but race not yet complete — skipping results")
                # Still load for weather/track data but never use results
                loaded[name] = sess
        else:
            loaded[name] = sess
            print(f"[SESSION] Loaded: {name}")
    except Exception as e:
        failed[name] = str(e)
        print(f"[SESSION] Failed: {name} — {e}")

if not any(k in loaded for k in ['Q', 'S', 'FP1']):
    print("[FATAL] No usable session data. Cannot proceed.")
    sys.exit(1)

# Extract driver list from best available session
# Priority: Q > S > SQ > FP1
drivers_df = None
for name in ['Q', 'S', 'SQ', 'FP1']:
    if name in loaded:
        sess = loaded[name]
        if sess.results is not None and len(sess.results) > 0:
            drivers_df = sess.results[[
                c for c in
                ['DriverNumber','Abbreviation','FullName','TeamName','TeamColor']
                if c in sess.results.columns
            ]].drop_duplicates(subset=['Abbreviation']).reset_index(drop=True)
            print(f"[DRIVERS] {len(drivers_df)} drivers extracted from {name}")
            break

if drivers_df is None or len(drivers_df) == 0:
    print("[FATAL] Cannot extract driver list from any session.")
    sys.exit(1)

DRIVERS = drivers_df['Abbreviation'].tolist()
N = len(DRIVERS)

parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')
parser.add_argument('--no-weather', action='store_true')
parser.add_argument('--save', action='store_true')
args, unknown = parser.parse_known_args()

qual_features = {}  # keyed by driver abbreviation

if 'Q' in loaded:
    q = loaded['Q']
    qr = q.results.copy() if q.results is not None else pd.DataFrame()

    # Best lap time: Q3 > Q2 > Q1
    def best_q_time(row):
        for col in ['Q3','Q2','Q1']:
            if col in row.index and pd.notna(row[col]):
                return row[col]
        return pd.NaT

    def td_sec(td):
        try:
            return float(td.total_seconds()) if pd.notna(td) else float('nan')
        except:
            return float('nan')

    if len(qr) > 0 and 'Abbreviation' in qr.columns:
        qr['_best'] = qr.apply(best_q_time, axis=1)
        if 'Position' in qr.columns and qr['Position'].notna().any():
            qr = qr.sort_values('Position').reset_index(drop=True)
        else:
            qr = qr.sort_values('_best').reset_index(drop=True)

        qr['qualifying_position']   = range(1, len(qr)+1)
        qr['best_lap_seconds']      = qr['_best'].apply(td_sec)

        # Guard: need at least one valid lap time for pole reference
        valid_times = qr['best_lap_seconds'].dropna()
        if len(valid_times) > 0:
            pole_sec                    = valid_times.iloc[0]
            qr['gap_to_pole_seconds']   = qr['best_lap_seconds'] - pole_sec
        else:
            qr['gap_to_pole_seconds']   = float('nan')

        qr['Q1_seconds']            = qr['Q1'].apply(td_sec) if 'Q1' in qr.columns else float('nan')
        qr['Q2_seconds']            = qr['Q2'].apply(td_sec) if 'Q2' in qr.columns else float('nan')
        qr['Q3_seconds']            = qr['Q3'].apply(td_sec) if 'Q3' in qr.columns else float('nan')

        # Teammate gap
        if 'TeamName' in qr.columns:
            teams = qr.groupby('TeamName')['best_lap_seconds'].transform('min')
            qr['q_teammate_delta'] = qr['best_lap_seconds'] - teams
        else:
            qr['q_teammate_delta'] = float('nan')

        for _, row in qr.iterrows():
            abr = row.get('Abbreviation','')
            if abr:
                qual_features[abr] = {
                    'qualifying_position' : row['qualifying_position'],
                    'gap_to_pole_seconds' : row['gap_to_pole_seconds'],
                    'best_lap_seconds'    : row['best_lap_seconds'],
                    'Q1_seconds'          : row.get('Q1_seconds', float('nan')),
                    'Q2_seconds'          : row.get('Q2_seconds', float('nan')),
                    'Q3_seconds'          : row.get('Q3_seconds', float('nan')),
                    'q_teammate_delta'    : row.get('q_teammate_delta', float('nan')),
                }
        print(f"[FEATURE] Q: extracted for {len(qual_features)} drivers")
    else:
        print("[FEATURE] Q: no usable qualifying results")

sprint_features = {}

def get_ontrack_finish(classified_pos, sprint_laps, abr, status=None):
    """Reconstruct on-track finish from last-lap Position, ignoring time penalties."""
    # If driver DNF/DSQ/retired, use classified position as-is
    if status and isinstance(status, str) and any(
        s in status.upper() for s in ['RETIRED', 'DNF', 'DSQ', 'MECHANICAL', 'ACCIDENT']
    ):
        return classified_pos
    # Try to get last-lap on-track position
    if sprint_laps is not None and len(sprint_laps) > 0:
        drv_laps = sprint_laps[sprint_laps['Driver'] == abr] if 'Driver' in sprint_laps.columns else pd.DataFrame()
        if len(drv_laps) > 0 and 'Position' in drv_laps.columns:
            last_lap = drv_laps.sort_values('LapNumber').iloc[-1] if 'LapNumber' in drv_laps.columns else drv_laps.iloc[-1]
            ontrack = last_lap.get('Position')
            if pd.notna(ontrack):
                return float(ontrack)
    # Fallback to classified
    return classified_pos

if 'S' in loaded:
    s = loaded['S']
    sr = s.results.copy() if s.results is not None else pd.DataFrame()
    sprint_laps_df = s.laps.copy() if hasattr(s, 'laps') and s.laps is not None else pd.DataFrame()

    if len(sr) > 0 and 'Position' in sr.columns:
        sr = sr.sort_values('Position').reset_index(drop=True)

        def get_sprint_pace(abr, sprint_session):
            '''
            Extract representative sprint race pace.
            More lenient filtering than FP1 long runs.
            '''
            laps = sprint_session.laps.pick_driver(abr) if hasattr(sprint_session, 'laps') else pd.DataFrame()
            if len(laps) == 0:
                return float('nan'), float('nan'), float('nan')

            if 'LapTime' not in laps.columns:
                return float('nan'), float('nan'), float('nan')

            # Convert to seconds
            times = laps['LapTime'].dropna().apply(
                lambda t: t.total_seconds()
            )

            # Filter obvious outliers: within 110% of driver's own best
            if len(times) > 0:
                best = times.min()
                clean = times[times <= best * 1.10]
            else:
                clean = times

            # Exclude first lap (standing start, always slow)
            if 'LapNumber' in laps.columns:
                not_first = laps['LapNumber'] > 1
                times_excl_first = laps[not_first]['LapTime'].dropna().apply(
                    lambda t: t.total_seconds()
                )
                if len(times_excl_first) > 0:
                    times_excl_first = times_excl_first[
                        times_excl_first <= times_excl_first.min() * 1.10
                    ]
                    if len(times_excl_first) >= 3:
                        clean = times_excl_first

            median = float(clean.median()) if len(clean) > 0 else float('nan')
            best   = float(clean.min())    if len(clean) > 0 else float('nan')
            std    = float(clean.std())    if len(clean) > 2 else float('nan')

            return median, best, std

        # Grid positions from sprint
        grid_col = 'GridPosition' if 'GridPosition' in sr.columns else None

        for _, row in sr.iterrows():
            abr = row.get('Abbreviation','')
            if not abr:
                continue
            classified_pos = float(row['Position']) if pd.notna(row.get('Position')) else float('nan')
            grid   = float(row[grid_col]) if grid_col and pd.notna(row.get(grid_col)) else float('nan')

            # On-track finish from last-lap Position data
            drv_status = row.get('Status', None)
            ontrack_pos = get_ontrack_finish(classified_pos, sprint_laps_df, abr, drv_status)
            had_penalty = 1 if (not np.isnan(classified_pos) and not np.isnan(ontrack_pos) and classified_pos != ontrack_pos) else 0

            gain   = (grid - ontrack_pos) if not any(
                np.isnan([grid, ontrack_pos])
            ) else float('nan')

            # Lap pace from sprint laps
            median_pace, best_pace, std_pace = get_sprint_pace(abr, s)

            # Penalty/incident flag from race control
            penalty_flag = 0
            if hasattr(s,'race_control_messages') and s.race_control_messages is not None:
                rcm = s.race_control_messages
                if 'Message' in rcm.columns:
                    driver_msgs = rcm[
                        rcm['Message'].str.contains(abr, na=False)
                    ]
                    penalty_flag = int(
                        driver_msgs['Message'].str.contains(
                            'PENALTY|INVESTIGATION|DISQUALIFIED', na=False
                        ).any()
                    )

            # Merge penalty detection: RCM or position mismatch
            if had_penalty:
                penalty_flag = 1

            s_grid_val = float(row[grid_col]) if grid_col and pd.notna(row.get(grid_col)) else float('nan')
            sprint_features[abr] = {
                'sprint_finish_position_classified' : classified_pos,
                'sprint_finish_position_ontrack'    : ontrack_pos,
                'sprint_had_time_penalty'           : had_penalty,
                'sprint_finish_position'            : ontrack_pos,  # scoring uses on-track
                'sprint_position_gain_loss'         : gain,
                'sprint_grid_position'              : s_grid_val,
                'sprint_lap_pace_median'            : median_pace,
                'sprint_lap_pace_best'              : best_pace,
                'sprint_consistency_std'             : std_pace,
                'sprint_penalty_flag'               : penalty_flag,
            }

    print(f"[FEATURE] S: extracted for {len(sprint_features)} drivers")

fp1_features = {}

if 'FP1' in loaded:
    fp1 = loaded['FP1']
    all_laps = fp1.laps.copy() if hasattr(fp1,'laps') else pd.DataFrame()

    if len(all_laps) > 0:
        # Filter accurate laps only
        if 'IsAccurate' in all_laps.columns:
            acc_laps = all_laps[all_laps['IsAccurate'] == True].copy()
        else:
            acc_laps = all_laps.copy()

        # Convert LapTime to seconds
        if 'LapTime' in acc_laps.columns:
            acc_laps['LapTime_s'] = acc_laps['LapTime'].apply(
                lambda t: t.total_seconds() if pd.notna(t) else float('nan')
            )

        # Long run detection:
        # A stint with 5+ consecutive laps on the same compound
        # excluding first 2 (out-lap + first flying) and last 1 (in-lap)
        # Weight longer stints more; use ±2% outlier removal
        def get_long_run_pace(driver_laps):
            if 'Stint' not in driver_laps.columns:
                return float('nan'), 0
            weighted_times = []
            total_clean_laps = 0
            for stint_id, stint in driver_laps.groupby('Stint'):
                stint = stint.sort_values('LapNumber')
                if len(stint) >= 5:
                    # Drop first 2 and last 1 lap of stint
                    core = stint.iloc[2:-1]
                    times = core['LapTime_s'].dropna().tolist()
                    # Remove outliers: keep laps within ±2% of stint median
                    if len(times) >= 3:
                        med = np.median(times)
                        clean = [t for t in times if med * 0.98 <= t <= med * 1.02]
                        if len(clean) >= 3:
                            stint_weight = len(clean)  # longer stints weighted more
                            weighted_times.append((np.median(clean), stint_weight))
                            total_clean_laps += len(clean)
            if not weighted_times:
                return float('nan'), 0
            # Weighted median by stint length
            total_w = sum(w for _, w in weighted_times)
            pace = sum(p * w for p, w in weighted_times) / total_w
            return float(pace), total_clean_laps

        fastest_overall = acc_laps.groupby('Driver')['LapTime_s'].min()
        fp1_pole_equiv  = fastest_overall.min()

        for abr in DRIVERS:
            drv_laps = acc_laps[acc_laps['Driver'] == abr]
            if len(drv_laps) == 0:
                fp1_features[abr] = {}
                continue

            best      = drv_laps['LapTime_s'].min()
            median    = drv_laps['LapTime_s'].median()
            std       = drv_laps['LapTime_s'].std()
            count     = len(drv_laps)
            long_run, lr_laps = get_long_run_pace(drv_laps)
            gap       = best - fp1_pole_equiv

            # Reliability: how much to trust long-run pace vs best-lap rank
            if lr_laps >= 8:
                lr_reliability = 1.0
            elif lr_laps >= 5:
                lr_reliability = 0.7
            elif lr_laps >= 3:
                lr_reliability = 0.4
            else:
                lr_reliability = 0.0  # no usable long-run data

            # Rank among all drivers
            rank = int((fastest_overall < best).sum()) + 1

            # Compounds used
            compounds = []
            if 'Compound' in drv_laps.columns:
                compounds = drv_laps['Compound'].dropna().unique().tolist()

            fp1_features[abr] = {
                'fp1_best_lap_seconds'   : float(best),
                'fp1_best_lap_gap'       : float(gap),
                'fp1_best_lap_rank'      : rank,
                'fp1_median_lap_pace'    : float(median),
                'fp1_long_run_pace'      : float(long_run),
                'fp1_long_run_lap_count' : lr_laps,
                'fp1_long_run_reliability': lr_reliability,
                'fp1_consistency_std'    : float(std),
                'fp1_lap_count'          : count,
                'fp1_compounds_used'     : compounds,
            }

        print(f"[FEATURE] FP1: extracted for {len(fp1_features)} drivers")

tyre_features = {}

for sess_name in ['S', 'FP1']:
    if sess_name not in loaded:
        continue
    sess = loaded[sess_name]
    laps = sess.laps.copy() if hasattr(sess,'laps') else pd.DataFrame()
    if len(laps) == 0 or 'LapTime' not in laps.columns:
        continue
    laps['LapTime_s'] = laps['LapTime'].apply(
        lambda t: t.total_seconds() if pd.notna(t) else float('nan')
    )

    for abr in DRIVERS:
        drv = laps[laps['Driver'] == abr].copy()
        if len(drv) < 3:
            continue

        stints = {}
        if 'Stint' in drv.columns and 'Compound' in drv.columns:
            for stint_id, sg in drv.groupby('Stint'):
                compound = sg['Compound'].mode().iloc[0] if len(sg) > 0 else 'UNKNOWN'
                times    = sg['LapTime_s'].dropna().tolist()
                if len(times) >= 3:
                    # Degradation proxy: slope of lap time over lap number
                    lap_nums = list(range(len(times)))
                    slope    = float(np.polyfit(lap_nums, times, 1)[0]) if len(times) >= 3 else 0.0
                    stints[str(stint_id)] = {
                        'compound'        : compound,
                        'lap_count'       : len(times),
                        'median_pace'     : float(np.median(times)),
                        'best_pace'       : float(np.min(times)),
                        'degradation_s_per_lap' : round(slope, 4),
                    }

        if abr not in tyre_features:
            tyre_features[abr] = {}

        tyre_features[abr][sess_name] = {
            'stint_count'  : len(stints),
            'stints'       : stints,
            'compounds'    : list({s['compound'] for s in stints.values()}),
            'avg_degradation' : float(np.mean([
                s['degradation_s_per_lap'] for s in stints.values()
            ])) if stints else float('nan'),
        }

print(f"[FEATURE] Tyre/stint: extracted for {len(tyre_features)} drivers")

weather_features = {
    'rain_risk'               : 0.0,
    'air_temp'                : float('nan'),
    'track_temp'              : float('nan'),
    'humidity'                : float('nan'),
    'weather_volatility_score': 0.0,
    'wet_race_adjustment'     : 0.0,
    'source'                  : 'none',
}

# Try FastF1 weather from race-day session (R or Q as proxy)
for sess_name in ['R', 'Q', 'S']:
    if sess_name in loaded:
        sess = loaded[sess_name]
        wd = getattr(sess, 'weather_data', None)
        if wd is not None and len(wd) > 0:
            try:
                weather_features['air_temp']   = float(wd['AirTemp'].mean())
                weather_features['track_temp'] = float(wd['TrackTemp'].mean()) if 'TrackTemp' in wd else float('nan')
                weather_features['humidity']   = float(wd['Humidity'].mean()) if 'Humidity' in wd else float('nan')
                rain_laps = wd['Rainfall'].sum() if 'Rainfall' in wd else 0
                weather_features['rain_risk']  = float(rain_laps / len(wd)) if len(wd) > 0 else 0.0
                weather_features['source']     = f'FastF1:{sess_name}'
                break
            except Exception as e:
                print(f"[WARN] Weather from {sess_name} failed: {e}")

# Open-Meteo fallback if FastF1 weather unavailable and --no-weather not set
if weather_features['source'] == 'none' and not args.no_weather:
    try:
        import urllib.request, json as _json
        # Miami International Autodrome coordinates
        lat, lon = 25.9581, -80.2389
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&hourly=temperature_2m,precipitation_probability,relative_humidity_2m"
            f"&forecast_days=1&timezone=America/New_York"
        )
        with urllib.request.urlopen(url, timeout=8) as r:
            wdata = _json.loads(r.read())
        # Race window: approximately 16:00–18:30 local (hours 16-18)
        hours = wdata['hourly']['time']
        race_idx = [i for i, h in enumerate(hours) if '16:00' <= h[-5:] <= '18:00']
        if race_idx:
            temps  = [wdata['hourly']['temperature_2m'][i] for i in race_idx]
            prec   = [wdata['hourly']['precipitation_probability'][i] for i in race_idx]
            humid  = [wdata['hourly']['relative_humidity_2m'][i] for i in race_idx]
            weather_features['air_temp']   = float(np.mean(temps))
            weather_features['humidity']   = float(np.mean(humid))
            weather_features['rain_risk']  = float(np.mean(prec)) / 100.0
            weather_features['source']     = 'Open-Meteo API'
    except Exception as e:
        print(f"[WARN] Open-Meteo weather fetch failed: {e}")

# Volatility and wet race adjustment
rain_risk = weather_features['rain_risk']
weather_features['weather_volatility_score'] = min(1.0, rain_risk * 2.0)
weather_features['wet_race_adjustment']       = 1.0 if rain_risk > 0.5 else 0.0

print(f"[WEATHER] Source: {weather_features['source']}")
print(f"[WEATHER] Air temp: {weather_features['air_temp']:.1f}°C  Rain risk: {rain_risk:.0%}")

FEATURES_PATH = 'data/features/race_features.parquet'
try:
    hist = pd.read_parquet(FEATURES_PATH)
except Exception:
    hist = pd.DataFrame()

# Step 2: Print ALL columns in debug mode so we can see what's there
if args.debug:
    print(f"[DEBUG] Parquet columns: {list(hist.columns)}")
    print(f"[DEBUG] Parquet shape: {hist.shape}")
    print(f"[DEBUG] First row sample:")
    print(hist.iloc[0].to_dict() if not hist.empty else "Empty DataFrame")

# Step 3: Try every possible driver column name variant
DRIVER_COL_CANDIDATES = [
    'driver_abbreviation', 'driver_code', 'abbreviation',
    'driver_id', 'driverCode', 'Driver', 'driver',
    'driver_ref', 'driverRef', 'code', 'driver_name'
]
driver_col = None
for candidate in DRIVER_COL_CANDIDATES:
    if candidate in hist.columns:
        # Verify it actually contains driver codes
        sample_vals = hist[candidate].dropna().astype(str).unique()[:20]
        # Check if any known 2024 driver codes appear
        known_codes = {'VER','NOR','LEC','HAM','RUS','SAI','PIA',
                       'ALO','STR','GAS','ALB','OCO','TSU','HUL',
                       'BOT','MAG','ZHO','SAR','RIC','LAW'}
        if any(code in sample_vals for code in known_codes):
            driver_col = candidate
            print(f"[HISTORY] Driver column confirmed: '{driver_col}'")
            break

# Step 4: If still None, scan all string columns for driver codes
if driver_col is None:
    for col in hist.select_dtypes(include='object').columns:
        sample = hist[col].dropna().astype(str).str.upper().unique()[:50]
        matches = sum(1 for v in sample if len(v) == 3 and v.isalpha())
        if matches > 5:
            driver_col = col
            print(f"[HISTORY] Driver column detected by heuristic: '{driver_col}'")
            break

# Step 5: If STILL None, print all column samples and exit cleanly
if driver_col is None:
    print("[WARN] Cannot find driver column. Printing column samples:")
    for col in hist.columns[:10]:
        print(f"  {col}: {hist[col].dropna().unique()[:5]}")
    print("[WARN] Skipping historical features — using global medians only")
    driver_col = hist.columns[0] if not hist.empty else None  # prevent crash

print(f"[HISTORY] Driver column: '{driver_col}'  Rows: {len(hist)}")

HIST_FEATURES = [
    f for f in [
        'rolling_avg_finish_5','rolling_points_5',
        'circuit_win_rate','circuit_avg_finish',
        'dnf_rate_last_10','constructor_points_standing',
        'teammate_quali_delta','career_poles'
    ] if f in hist.columns
]

global_medians = hist[HIST_FEATURES].median() if HIST_FEATURES else pd.Series(dtype=float)

# Miami-specific history rows
circuit_col = next(
    (c for c in ['circuit_id','circuit_ref','EventName','event_name']
     if c in hist.columns), None
)
hist_miami = hist[
    hist[circuit_col].astype(str).str.contains('miami|Miami', na=False)
] if circuit_col else hist

def get_driver_history(abr):
    if driver_col is None or hist.empty:
        return pd.DataFrame()
    mask = hist[driver_col].astype(str).str.upper() == abr.strip().upper()
    rows = hist[mask]
    if args.debug and len(rows) == 0:
        print(f"[DEBUG] No rows found for {abr} in column '{driver_col}'")
        print(f"[DEBUG] Sample values in column: {hist[driver_col].dropna().unique()[:10]}")
    return rows.sort_values(
        'race_date' if 'race_date' in rows.columns else hist.columns[0],
        ascending=False
    ) if len(rows) > 0 else pd.DataFrame()

def get_hist_features(abr):
    rows = get_driver_history(abr)
    feats = {}
    for feat in HIST_FEATURES:
        vals = rows[feat].dropna() if len(rows) > 0 and feat in rows.columns else pd.Series(dtype=float)
        feats[feat] = float(vals.iloc[0]) if len(vals) > 0 else float(global_medians.get(feat, 0))
    # Miami-specific
    if driver_col is not None and not hist_miami.empty:
        miami_rows = hist_miami[
            hist_miami[driver_col].astype(str).str.upper() == abr.strip().upper()
        ]
        feats['miami_avg_finish'] = float(miami_rows['circuit_avg_finish'].mean()) \
            if circuit_col and 'circuit_avg_finish' in miami_rows.columns \
            and len(miami_rows) > 0 else float(global_medians.get('circuit_avg_finish', 10))
    else:
        feats['miami_avg_finish'] = float(global_medians.get('circuit_avg_finish', 10))
    return feats

def safe_load(path):
    try:
        return joblib.load(path)
    except ModuleNotFoundError as e:
        if 'src' in str(e):
            import pickle
            class _Safe(pickle.Unpickler):
                def find_class(self, mod, name):
                    if mod.startswith('src.'):
                        return object
                    return super().find_class(mod, name)
            with open(path,'rb') as f:
                return _Safe(f).load()
        raise

MODEL_PATHS = {
    'race_finish' : [
        'models/advanced/race_finish_advanced_post_qualifying.joblib',
        'models/baseline/race_finish_post_qualifying.joblib',
    ],
    'podium' : [
        'models/advanced/podium_advanced_post_qualifying.joblib',
        'models/baseline/podium_post_qualifying.joblib',
    ],
    'top10' : [
        'models/advanced/top10_advanced_post_qualifying.joblib',
        'models/baseline/top10_post_qualifying.joblib',
    ],
}

ml_models = {}
for key, paths in MODEL_PATHS.items():
    for path in paths:
        if os.path.exists(path):
            try:
                ml_models[key] = safe_load(path)
                print(f"[MODEL] Loaded: {path}")
                break
            except Exception as e:
                print(f"[WARN] Failed to load {path}: {e}")

# Load expected columns
try:
    with open('reports/advanced_model_input_columns.json') as f:
        col_spec = json.load(f)
except Exception:
    col_spec = {}

# Build ML inference dataframe
TARGET_WORDS = ['target','race_result','finish_position',
                'podium_actual','winner','classified']

def build_ml_row(abr):
    row = {}
    row.update(qual_features.get(abr, {}))
    row.update(sprint_features.get(abr, {}))
    row.update(fp1_features.get(abr, {}))
    row.update(get_hist_features(abr))
    # Weather
    row['air_temp']   = weather_features['air_temp']
    row['rain_risk']  = weather_features['rain_risk']
    row['humidity']   = weather_features['humidity']
    return row

rows = {abr: build_ml_row(abr) for abr in DRIVERS}
ml_df = pd.DataFrame(rows).T

ml_predictions = {}

for model_key, expected_key in [
    ('race_finish', 'race_finish_advanced_post_qualifying'),
    ('podium',      'podium_advanced_post_qualifying'),
    ('top10',       'top10_advanced_post_qualifying'),
]:
    if model_key not in ml_models:
        continue
    raw_cols = col_spec.get(expected_key) or col_spec.get(expected_key.replace('_advanced', '')) or []
    expected_cols = [
        c for c in raw_cols
        if not any(t in c.lower() for t in TARGET_WORDS)
    ]
    model = ml_models[model_key]
    # Build X with expected columns, fill missing with column medians
    X = pd.DataFrame(index=DRIVERS)
    for col in expected_cols:
        if col in ml_df.columns:
            X[col] = pd.to_numeric(ml_df[col], errors='coerce')
        else:
            X[col] = float('nan')
    # Fill NaN with training medians from parquet
    for col in X.columns:
        if X[col].isna().any():
            if col in hist.columns and pd.api.types.is_numeric_dtype(hist[col]):
                fill_val = float(hist[col].median())
            else:
                fill_val = 0.0
            X[col] = X[col].fillna(fill_val)

    try:
        if model_key == 'race_finish':
            preds = model.predict(X)
            ml_predictions['predicted_finish'] = dict(zip(DRIVERS, preds))
        else:
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(X)[:, 1]
            else:
                proba = model.predict(X).astype(float)
            ml_predictions[model_key + '_proba'] = dict(zip(DRIVERS, proba))
        print(f"[ML] {model_key} predictions computed for {len(DRIVERS)} drivers")
    except Exception as e:
        print(f"[WARN] ML prediction failed for {model_key}: {e}")

# Lower race_intel_score = stronger predicted race pace
# Each sub-score normalized to [0,1] where 0=best, 1=worst

def normalize_rank(values_dict, higher_is_better=False):
    """Convert dict of raw values to [0,1] normalized scores."""
    abrs  = list(values_dict.keys())
    vals  = [values_dict[a] for a in abrs]
    valid = [v for v in vals if not np.isnan(v)]
    if not valid:
        return {a: 0.5 for a in abrs}
    vmin, vmax = min(valid), max(valid)
    result = {}
    for a, v in zip(abrs, vals):
        if np.isnan(v):
            result[a] = 0.5  # neutral for missing
        elif vmax == vmin:
            result[a] = 0.0
        else:
            norm = (v - vmin) / (vmax - vmin)
            result[a] = (1 - norm) if higher_is_better else norm
    return result

def compute_upgrade_delta(abr, drivers_df, qual_features, fp1_features, sprint_features):
    '''
    Upgrade effectiveness proxy:
    Compare each driver's gap_to_pole in FP1 vs Q.
    If gap improved significantly from FP1 to Q,
    the upgrade worked and the car is getting faster through weekend.
    A shrinking gap = positive upgrade delta.
    '''
    fp1_gap = fp1_features.get(abr, {}).get('fp1_best_lap_gap', float('nan'))
    q_gap   = qual_features.get(abr, {}).get('gap_to_pole_seconds', float('nan'))

    if any(np.isnan([fp1_gap, q_gap])):
        return 0.0  # neutral if data missing

    # Positive delta = improvement from FP1 to Q = upgrade working
    delta = fp1_gap - q_gap  # positive = improved
    # Normalize to [-1, +1] range using 1.0s as max expected swing
    normalized = max(-1.0, min(1.0, delta / 1.0))
    return float(normalized)

def compute_execution_risk(abr, sprint_features, qual_features):
    '''
    Execution risk = probability of losing positions at/after race start.
    Uses ON-TRACK sprint position (not classified) to avoid double-penalty.
    '''
    risk = 0.0

    # Signal 1: Sprint grid position vs on-track sprint finish
    s_grid   = sprint_features.get(abr, {}).get('sprint_grid_position', float('nan'))
    s_finish = sprint_features.get(abr, {}).get('sprint_finish_position_ontrack', float('nan'))

    if not any(np.isnan([s_grid, s_finish])):
        positions_lost = s_finish - s_grid  # positive = lost positions
        if positions_lost > 3:
            risk += 0.35
        elif positions_lost > 1:
            risk += 0.18
        elif positions_lost < -2:
            risk -= 0.10   # gained places = good starter

    # Signal 2: Small discipline penalty if time penalty occurred
    had_penalty = sprint_features.get(abr, {}).get('sprint_had_time_penalty', 0)
    if had_penalty:
        risk += 0.08

    # Signal 3: Front-row pressure
    q_pos = qual_features.get(abr, {}).get('qualifying_position', 10)
    if q_pos <= 2:
        risk += 0.05

    return float(min(1.0, max(0.0, risk)))

# --- Precompute field-wide qualifying gap spread for FIX 3 ---
all_q_gaps = [
    qf.get('gap_to_pole_seconds', float('nan'))
    for qf in qual_features.values()
]
all_q_gaps_valid = [g for g in all_q_gaps if not np.isnan(g) and g >= 0]
max_q_gap = max(all_q_gaps_valid) if all_q_gaps_valid else 5.0

race_intel = {}  # final race intel scores per driver
# Store per-driver component scores for debug/guardrails
component_scores = {}

for abr in DRIVERS:
    qf  = qual_features.get(abr, {})
    sf  = sprint_features.get(abr, {})
    fp  = fp1_features.get(abr, {})
    tf  = tyre_features.get(abr, {})
    hf  = get_hist_features(abr)

    # --- A. Qualifying / track position score (18%) ---
    # FIX 3: 50/50 position rank + gap-to-pole normalized against field spread
    q_pos  = qf.get('qualifying_position', N/2)
    q_gap  = qf.get('gap_to_pole_seconds', 5.0)
    q_pos_score = (q_pos - 1) / max(N - 1, 1)
    q_gap_score = q_gap / max_q_gap if max_q_gap > 0 else 0.5
    q_score = 0.50 * q_pos_score + 0.50 * q_gap_score

    # --- B. Sprint race result and pace (30%) ---
    # Uses on-track finish position (FIX 1)
    s_pos   = sf.get('sprint_finish_position', N/2)
    s_gain  = sf.get('sprint_position_gain_loss', 0)
    s_score_pos  = (s_pos - 1) / max(N - 1, 1)
    s_score_gain = max(0, min(1, (10 - s_gain) / 20))
    sprint_score = s_score_pos * 0.6 + s_score_gain * 0.4

    # --- C. Long-run / FP1 pace (25%) ---
    # FIX 2: Blend long-run pace with best-lap rank based on reliability
    fp1_rank     = fp.get('fp1_best_lap_rank', N//2)
    fp1_rank_score = (fp1_rank - 1) / max(N - 1, 1)
    lr_reliability = fp.get('fp1_long_run_reliability', 0.0)
    lr_pace = fp.get('fp1_long_run_pace', float('nan'))
    if not np.isnan(lr_pace):
        # Normalize long-run pace across field
        all_lr = [fp1_features.get(d, {}).get('fp1_long_run_pace', float('nan')) for d in DRIVERS]
        valid_lr = [v for v in all_lr if not np.isnan(v)]
        if valid_lr and max(valid_lr) > min(valid_lr):
            lr_pace_score = (lr_pace - min(valid_lr)) / (max(valid_lr) - min(valid_lr))
        else:
            lr_pace_score = 0.5
    else:
        lr_pace_score = fp1_rank_score  # fallback

    # Blend: reliability weights how much to trust long-run vs best-lap
    fp1_score = lr_reliability * lr_pace_score + (1 - lr_reliability) * fp1_rank_score

    # --- D. Tyre / degradation (5%) ---
    s_tyres   = tf.get('S', {})
    avg_deg   = s_tyres.get('avg_degradation', 0.2)
    tyre_score = min(1.0, max(0.0, (avg_deg + 0.1) / 0.5)) if not np.isnan(avg_deg) else 0.3

    # --- E. Upgrade Delta (10%) ---
    upgrade_delta = compute_upgrade_delta(abr, drivers_df, qual_features, fp1_features, sprint_features)
    upgrade_score = 1.0 - (upgrade_delta + 1.0) / 2.0

    # --- F. Driver execution risk (9%) ---
    exec_score = compute_execution_risk(abr, sprint_features, qual_features)

    # --- G. Weather adjustment (3%) ---
    rain_risk  = weather_features['rain_risk']
    wet_adjust = weather_features['wet_race_adjustment']
    miami_hist = hf.get('miami_avg_finish', 10.0)
    weather_score = (rain_risk * 0.5) + ((miami_hist - 1) / max(N-1,1) * wet_adjust * 0.5)

    # --- Composite race intel score (lower = better predicted race result) ---
    race_intel[abr] = (
        0.18 * q_score      +
        0.30 * sprint_score +
        0.25 * fp1_score    +
        0.05 * tyre_score   +
        0.10 * upgrade_score+
        0.09 * exec_score   +
        0.03 * weather_score
    )

    # Store component scores for debug and guardrails
    component_scores[abr] = {
        'q_score': q_score, 'q_pos_score': q_pos_score, 'q_gap_score': q_gap_score,
        'sprint_score': sprint_score, 'fp1_score': fp1_score,
        'lr_pace_score': lr_pace_score, 'lr_reliability': lr_reliability,
        'tyre_score': tyre_score, 'upgrade_score': upgrade_score,
        'exec_score': exec_score, 'weather_score': weather_score,
    }

print(f"[INTEL] Race intelligence scores computed for {len(race_intel)} drivers")

# Normalize ML predictions to [0,1] scores
# Lower finish prediction = better = higher score
n_drivers = len(DRIVERS)

ml_finish_raw  = ml_predictions.get('predicted_finish', {a: n_drivers/2 for a in DRIVERS})
ml_podium_raw  = ml_predictions.get('podium_proba',     {a: 0.1 for a in DRIVERS})

# Normalize finish: lower raw = higher normalized score
ml_finish_norm = normalize_rank(ml_finish_raw, higher_is_better=False)
# Podium proba: higher = better
ml_podium_norm = normalize_rank(ml_podium_raw, higher_is_better=True)

# ML combined score (lower = better)
ml_score = {
    a: 0.5 * ml_finish_norm[a] + 0.5 * (1 - ml_podium_norm[a])
    for a in DRIVERS
}

# Race intel score already normalized (lower = better)
# Final ensemble
WEIGHT_CURRENT_WEEKEND = 0.75   # dominates — 2026 new regs
WEIGHT_HISTORICAL_ML   = 0.25   # supporting signal only

final_scores = {}
for abr in DRIVERS:
    intel = race_intel.get(abr, 0.5)
    ml    = (
        (0.15 / 0.25) * (1 - ml_podium_norm.get(abr, 0.5)) +
        (0.10 / 0.25) * ml_finish_norm.get(abr, 0.5)
    )
    final_scores[abr] = WEIGHT_CURRENT_WEEKEND * intel + WEIGHT_HISTORICAL_ML * ml

# Sort: lower score = better predicted result
raw_model_ranking = sorted(final_scores.items(), key=lambda x: x[1])

# Tie-break function
def get_tiebreak_fields(abr):
    return (
        qual_features.get(abr, {}).get('qualifying_position', 99),
        sprint_features.get(abr, {}).get('sprint_finish_position', 99),
        fp1_features.get(abr, {}).get('fp1_long_run_pace', 999),
        -(ml_podium_raw.get(abr, 0)),
    )

raw_model_ranking = sorted(
    final_scores.items(),
    key=lambda x: (round(x[1], 6), get_tiebreak_fields(x[0]))
)

# ============================================================
# ANALYST ADJUSTMENT LAYER
# ============================================================

def _build_execution_prior(abr, hist_df, driver_col):
    """Build driver execution prior from historical data without hardcoding names."""
    if driver_col is None or hist_df.empty:
        return 0.0  # neutral
    mask = hist_df[driver_col].astype(str).str.upper() == abr.strip().upper()
    rows = hist_df[mask]
    if len(rows) == 0:
        return 0.0
    prior = 0.0
    n = 0
    # Finish vs qualifying conversion
    for col_f, col_q in [('circuit_avg_finish','circuit_avg_quali'),
                          ('rolling_avg_finish_5',None)]:
        if col_f in rows.columns:
            avg_f = rows[col_f].dropna().mean()
            if not np.isnan(avg_f):
                # Lower avg finish = better conversion = positive prior
                prior += max(0, (10 - avg_f) / 10)
                n += 1
    # DNF rate
    if 'dnf_rate_last_10' in rows.columns:
        dnf = rows['dnf_rate_last_10'].dropna().mean()
        if not np.isnan(dnf):
            prior -= dnf * 0.5  # penalize unreliable
            n += 1
    # Podium conversion
    if 'circuit_win_rate' in rows.columns:
        wr = rows['circuit_win_rate'].dropna().mean()
        if not np.isnan(wr):
            prior += wr * 0.3
            n += 1
    return float(prior / max(n, 1))

def analyst_adjustment_layer(raw_ranked, driver_features, comp_scores, context):
    """
    Apply race-domain analyst rules as score adjustments.
    No driver names are hardcoded. All rules are data-driven.
    Lower score = better. Negative adjustment = improvement.
    """
    qf = driver_features['qual']
    sf = driver_features['sprint']
    fp = driver_features['fp1']
    rain = context.get('rain_risk', 0.0)
    N = len(raw_ranked)

    # Compute field medians for relative comparisons
    all_pod = [context['ml_podium'].get(a, 0) for a, _ in raw_ranked]
    pod_median = float(np.median(all_pod)) if all_pod else 0.1

    adjusted = {}
    reasons = {}
    audit = []

    for abr, raw_score in raw_ranked:
        adj = 0.0
        r = []
        q_pos = qf.get(abr, {}).get('qualifying_position', 99)
        q_gap = qf.get(abr, {}).get('gap_to_pole_seconds', 5.0)
        s_on = sf.get(abr, {}).get('sprint_finish_position_ontrack', 99)
        s_cl = sf.get(abr, {}).get('sprint_finish_position_classified', 99)
        s_grid = sf.get(abr, {}).get('sprint_grid_position', 99)
        s_pen = sf.get(abr, {}).get('sprint_had_time_penalty', 0)
        lr_rank = fp.get(abr, {}).get('fp1_best_lap_rank', N // 2)
        lr_rel = fp.get(abr, {}).get('fp1_long_run_reliability', 0.0)
        cs = comp_scores.get(abr, {})
        exec_risk = cs.get('exec_score', 0.0)
        tyre_sc = cs.get('tyre_score', 0.3)
        ml_pod = context['ml_podium'].get(abr, 0.0)
        hist_prior = _build_execution_prior(abr, context['hist'], context['driver_col'])

        # Count major negatives
        negatives = 0
        if s_on - s_grid > 3: negatives += 1
        if lr_rank > 8: negatives += 1
        if tyre_sc > 0.6: negatives += 1
        if exec_risk > 0.35: negatives += 1
        if ml_pod < pod_median: negatives += 1

        # Rule 1: Front-row protection
        if q_pos <= 2:
            bonus = -0.04 if q_pos == 1 else -0.03
            adj += bonus
            r.append(f"front-row P{q_pos} protection ({bonus:+.3f})")
            if negatives < 2:
                # Extra protection if not enough negative evidence
                adj -= 0.02
                r.append("insufficient negatives for large drop")

        # Rule 2: Pole sitter protection
        if q_pos == 1 and lr_rank <= 5:
            severe = (exec_risk > 0.45 or tyre_sc > 0.7 or s_on > 8)
            if not severe:
                adj -= 0.02
                r.append("pole + top-5 long-run protected")
            if s_pen and not severe:
                adj -= 0.01
                r.append("sprint penalty treated as discipline, not pace")

        # Rule 3: Sprint winner boost
        if s_on == 1:
            adj -= 0.035
            r.append("sprint winner race-pace boost")
            if q_pos <= 5:
                adj -= 0.015
                r.append("sprint winner + strong grid")

        # Rule 4: Sprint podium boost
        if 1 < s_on <= 3:
            adj -= 0.02
            r.append(f"sprint P{int(s_on)} podium boost")
            if q_pos <= 7:
                adj -= 0.01
                r.append("sprint podium + top-7 grid")

        # Rule 5: Qualifying + Sprint consistency
        if q_pos <= 4 and s_on <= 5:
            adj -= 0.015
            r.append("qual-sprint consistency")
        if q_pos <= 3 and s_on <= 3:
            adj -= 0.02
            r.append("major qual-sprint consistency")

        # Rule 6: Long-run confidence
        if lr_rel < 0.6:
            # Reduce any FP1-based advantage
            fp1_component = cs.get('fp1_score', 0.5)
            if fp1_component < 0.15:  # driver benefited a lot from FP1
                penalty = 0.01
                adj += penalty
                r.append(f"short FP1 sample discount (+{penalty:.3f})")
        elif lr_rel >= 0.8 and lr_rank <= 3:
            adj -= 0.01
            r.append("high-confidence long-run pace")

        # Rule 7: Execution prior from history
        if hist_prior > 0.15:
            bonus = -min(0.02, hist_prior * 0.05)
            adj += bonus
            r.append(f"historical execution prior ({bonus:+.3f})")
        elif hist_prior < -0.1:
            pen = min(0.015, abs(hist_prior) * 0.04)
            adj += pen
            r.append(f"historical reliability concern (+{pen:.3f})")

        # For rookies/new drivers with no history but strong weekend
        if hist_prior == 0.0 and q_pos <= 3 and s_on <= 5:
            adj -= 0.01
            r.append("strong weekend form (limited history)")

        # Rule 8: Weather uncertainty
        if rain > 0.3:
            if hist_prior > 0.1:
                adj -= 0.01
                r.append("wet-weather execution advantage")
            if exec_risk > 0.3:
                adj += 0.01
                r.append("wet-weather risk amplified")

        adjusted[abr] = raw_score + adj
        reasons[abr] = r

    # Re-rank
    adj_ranked = sorted(adjusted.items(), key=lambda x: (round(x[1], 6), get_tiebreak_fields(x[0])))
    adj_rank_map = {a: i+1 for i, (a, _) in enumerate(adj_ranked)}

    # Rule 9: Sanity audit
    for abr in [a for a, _ in adj_ranked]:
        qp = qf.get(abr, {}).get('qualifying_position', 99)
        s_on = sf.get(abr, {}).get('sprint_finish_position_ontrack', 99)
        rk = adj_rank_map[abr]
        if qp == 1 and rk > 5:
            audit.append(f"Pole {abr} at P{rk}: {', '.join(reasons.get(abr,[]))}")
        if qp == 2 and rk > 6:
            audit.append(f"P2 {abr} at P{rk}: {', '.join(reasons.get(abr,[]))}")
        if s_on == 1 and rk > 5:
            audit.append(f"Sprint winner {abr} at P{rk}: {', '.join(reasons.get(abr,[]))}")

    return adj_ranked, adjusted, reasons, audit

# Build context for analyst layer
analyst_context = {
    'rain_risk': weather_features['rain_risk'],
    'ml_podium': ml_podium_raw,
    'hist': hist,
    'driver_col': driver_col,
}
driver_features_bundle = {
    'qual': qual_features,
    'sprint': sprint_features,
    'fp1': fp1_features,
}

analyst_adjusted_ranking, adjusted_scores, adjustment_reasons, audit_flags = \
    analyst_adjustment_layer(raw_model_ranking, driver_features_bundle, component_scores, analyst_context)

# Final prediction uses analyst-adjusted ranking
ranked = analyst_adjusted_ranking
top3 = ranked[:3]


# Confidence for 2026 out-of-sample predictions
# Maximum is Medium-High — never High for 2026 new regulations

data_score = 0
if 'Q'   in loaded: data_score += 25   # qualifying = strong grid signal
if 'S'   in loaded: data_score += 35   # sprint race = strongest signal
if 'SQ'  in loaded: data_score += 10
if 'FP1' in loaded: data_score += 15
if weather_features['source'] != 'none': data_score += 5
n_with_history = sum(1 for a in DRIVERS if len(get_driver_history(a)) > 0)
if n_with_history > 10: data_score += 10   # historical context available

# Score gap between P3 and P4
p3_gap = ranked[3][1] - ranked[2][1] if len(ranked) >= 4 else 0
p3_stable = p3_gap > 0.03

# Agreement: do sprint top3 and final top3 overlap?
sprint_top3 = sorted(
    [a for a in DRIVERS if sprint_features.get(a, {}).get('sprint_finish_position')],
    key=lambda a: sprint_features[a]['sprint_finish_position']
)[:3]
final_top3_drivers = [a for a, _ in ranked[:3]]
agreement = len(set(sprint_top3) & set(final_top3_drivers))

if data_score >= 80 and p3_stable and agreement >= 2:
    confidence = 'Medium-High'   # max for 2026
elif data_score >= 60 and agreement >= 1:
    confidence = 'Medium'
elif data_score >= 40:
    confidence = 'Medium-Low'
else:
    confidence = 'Low'

# Hard cap — never output High for 2026 new regulation season
if confidence == 'High':
    confidence = 'Medium-High'

print(f"[CONFIDENCE] Data score: {data_score}/100  Level: {confidence}")

def get_full_name(abr):
    row = drivers_df[drivers_df['Abbreviation'] == abr]
    return row['FullName'].values[0] if len(row) > 0 and 'FullName' in row.columns else abr

def get_team(abr):
    row = drivers_df[drivers_df['Abbreviation'] == abr]
    return row['TeamName'].values[0] if len(row) > 0 and 'TeamName' in row.columns else ''

# Why bullets — one per top3 driver, only real signals
def why_bullet(abr, rank):
    reasons = []

    qp = qual_features.get(abr, {}).get('qualifying_position')
    sp = sprint_features.get(abr, {}).get('sprint_finish_position')
    sg = sprint_features.get(abr, {}).get('sprint_grid_position')
    lr = fp1_features.get(abr, {}).get('fp1_long_run_pace')
    mp = ml_podium_raw.get(abr, None)
    ud = compute_upgrade_delta(abr, drivers_df, qual_features,
                               fp1_features, sprint_features)
    er = compute_execution_risk(abr, sprint_features, qual_features)

    # Sprint result context
    if sp and sg and not any(np.isnan([sp, sg])):
        gain = sg - sp
        if gain > 2:
            reasons.append(f"gained {int(gain)} places in sprint (P{int(sg)}→P{int(sp)})")
        elif sp <= 3:
            reasons.append(f"P{int(sp)} in sprint race")
        elif gain < -2:
            reasons.append(f"lost {int(abs(gain))} places in sprint — start risk")

    # Qualifying
    if qp:
        reasons.append(f"P{int(qp)} on grid")

    # Long run pace
    if lr and not np.isnan(lr):
        reasons.append(f"long-run pace {lr:.2f}s/lap in FP1")

    # Upgrade working
    if ud > 0.2:
        reasons.append("upgrade improving through weekend")

    # Execution risk warning
    if er > 0.4:
        reasons.append(f"! start execution risk flagged (sprint data)")

    # Model signal
    if mp and mp > 0.35:
        reasons.append(f"historical model: {mp:.0%} podium probability")

    return ' - '.join(reasons) if reasons else 'strong weekend signals'

sep = '-' * 52
print(f"\n{sep}")
print(f"  GRID ORACLE - 2026 MIAMI GP RACE INTELLIGENCE")
print(sep)
for i, (abr, score) in enumerate(top3, 1):
    print(f"  P{i}  {abr:<4} -  {get_full_name(abr)}")
print()
print(f"  Confidence : {confidence}")
sessions_used = ', '.join(loaded.keys())
print(f"  Data used  : {sessions_used}" +
      (f" + {weather_features['source']}" if weather_features['source'] != 'none' else ''))
print(f"  Signal     : 2026 Miami weekend pace + Grid Oracle model inference")
print()
print("  Mode       : Analyst-adjusted race intelligence")
print("  Historical : " + ("Used" if n_with_history > 10 else "Neutral"))
print()
print("  Why top 3:")
for i, (abr, _) in enumerate(top3, 1):
    r = adjustment_reasons.get(abr, [])
    reason_str = ', '.join(r) if r else 'strong weekend signals'
    print(f"  P{i} {abr}: {reason_str}")
print()
print("  Warnings:")
print("  - 2026 is out-of-sample for old ML models")
print("  - Safety car, starts, tyre strategy, and weather can change the result")
print("  - Educational ML inference only")
print(sep)

# --- FIX 5: Audit guardrails (warnings only, never force ranking) ---
if audit_flags:
    print("\n[AUDIT WARNINGS]")
    for flag in audit_flags:
        print(f"  - {flag}")

# --- FIX 6: Enhanced debug output ---
if args.debug:
    print("\n[DEBUG] 1. RAW MODEL RANKING")
    for i, (abr, score) in enumerate(raw_model_ranking, 1):
        print(f"  {i:02d} {abr:<4} - Score: {score:.4f}")

    print("\n[DEBUG] 2. ANALYST ADJUSTMENTS (Top 10)")
    for abr, score in raw_model_ranking[:10]:
        adj = adjusted_scores.get(abr, score) - score
        adj_score = adjusted_scores.get(abr, score)
        reasons = ', '.join(adjustment_reasons.get(abr, []))
        print(f"  {abr:<4} | Raw: {score:.4f} | Adj: {adj:+.4f} | Final: {adj_score:.4f} | Reasons: {reasons}")

    print("\n[DEBUG] 3. FINAL ANALYST-ADJUSTED RANKING")
    cols = ['Rank','Drv','Team','QP','SOntrk','SClass','FP1LR','LRLaps','LRRel','MLPod',
            'RawScor','Adjust','AdjScor','Reasons']
    header = '  '.join(f"{c:<7}" for c in cols[:-1]) + "  Reasons"
    print(header)
    print('-' * len(header))
    for rank_i, (abr, fscore) in enumerate(ranked, 1):
        qp   = qual_features.get(abr,{}).get('qualifying_position','?')
        s_on = sprint_features.get(abr,{}).get('sprint_finish_position_ontrack','?')
        s_cl = sprint_features.get(abr,{}).get('sprint_finish_position_classified','?')
        lr   = fp1_features.get(abr,{}).get('fp1_long_run_pace', float('nan'))
        lrl  = fp1_features.get(abr,{}).get('fp1_long_run_lap_count', 0)
        lrr  = fp1_features.get(abr,{}).get('fp1_long_run_reliability', 0.0)
        mp   = ml_podium_raw.get(abr, float('nan'))
        raw  = dict(raw_model_ranking).get(abr, float('nan'))
        adj  = fscore - raw if not np.isnan(raw) else 0.0
        reasons = ', '.join(adjustment_reasons.get(abr, []))

        def _f(v, fmt='.3f'):
            return f"{v:{fmt}}" if isinstance(v, float) and not np.isnan(v) else str(v)

        vals = [
            f"{rank_i:<7}", f"{abr:<7}", f"{get_team(abr)[:7]:<7}",
            f"{str(qp):<7}", f"{str(s_on):<7}", f"{str(s_cl):<7}",
            f"{_f(lr):<7}", f"{str(lrl):<7}", f"{_f(lrr):<7}",
            f"{_f(mp):<7}",
            f"{_f(raw,'.4f'):<7}",
            f"{_f(adj,'.4f'):<7}",
            f"{_f(fscore,'.4f'):<7}",
            reasons
        ]
        print('  '.join(vals))

if args.save or True:  # always save
    output = {
        'event'         : {'season': SEASON, 'round': ROUND,
                           'name': 'Miami Grand Prix', 'stage': 'post_qualifying'},
        'final_prediction' : [
            {'position': i+1, 'driver': abr,
             'full_name': get_full_name(abr), 'team': get_team(abr),
             'final_score': round(score, 6),
             'qualifying_position': qual_features.get(abr,{}).get('qualifying_position'),
             'sprint_finish_ontrack': sprint_features.get(abr,{}).get('sprint_finish_position_ontrack'),
            }
            for i, (abr, score) in enumerate(top3)
        ],
        'analyst_adjusted_ranking'  : [
            {'rank': i+1, 'driver': abr, 'adjusted_score': round(score, 6),
             'raw_score': round(dict(raw_model_ranking).get(abr, float('nan')), 6),
             'adjustment': round(score - dict(raw_model_ranking).get(abr, float('nan')), 6),
             'reasons': adjustment_reasons.get(abr, [])
            }
            for i, (abr, score) in enumerate(ranked)
        ],
        'raw_model_ranking': [
            {'rank': i+1, 'driver': abr, 'score': round(score, 6)}
            for i, (abr, score) in enumerate(raw_model_ranking)
        ],
        'analyst_adjustments': adjustment_reasons,
        'audit_flags': audit_flags,
        'confidence'    : confidence,
        'sessions_used' : list(loaded.keys()),
        'sessions_failed': failed,
        'weather'       : weather_features,
        'warnings'      : [
            'ML models trained on 2018-2024. 2026 is out-of-sample.',
            'Weather, safety car, and start incidents can change result.',
        ],
        'disclaimer'    : 'Educational ML inference system. Not a betting tool.',
        'timestamp'     : datetime.now(timezone.utc).isoformat(),
    }
    os.makedirs('reports', exist_ok=True)
    with open('reports/miami_2026_race_intel_prediction.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n[SAVED] reports/miami_2026_race_intel_prediction.json")

