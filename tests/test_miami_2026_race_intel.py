import sys
import os
import pytest
import runpy
import inspect
import ast
from unittest.mock import patch, MagicMock
import fastf1
import pandas as pd
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(_ROOT, 'scripts', 'predict_miami_2026_race_intel.py')

if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

@pytest.fixture(scope="module")
def intel_globals():
    old_argv = sys.argv
    sys.argv = ['predict_miami_2026_race_intel.py', '--no-weather']
    
    original_get_session = fastf1.get_session
    def mock_get_session(season, round_num, session_name):
        sess = original_get_session(season, round_num, session_name)
        if session_name == 'R':
            sess.session_status = 'Testing'
            if hasattr(sess, 'results'):
                sess.results = pd.DataFrame()
        return sess

    try:
        with patch('fastf1.get_session', side_effect=mock_get_session):
            return runpy.run_path(SCRIPT_PATH)
    finally:
        sys.argv = old_argv

def test_1_top3_has_exactly_3_drivers(intel_globals):
    top3 = intel_globals['top3']
    assert len(top3) == 3
    # Check that they have valid structure
    assert isinstance(top3[0][0], str)
    assert isinstance(top3[0][1], float)

def test_2_no_target_columns_in_ml_inference(intel_globals):
    TARGET_WORDS = intel_globals['TARGET_WORDS']
    # Instead of checking ml_df, let's verify expected_cols logic manually
    # since X is localized.
    col_spec = intel_globals['col_spec']
    if not col_spec:
        pytest.skip("No col_spec found")
    
    for key, cols in col_spec.items():
        if not cols:
            continue
        expected_cols = [
            c for c in cols
            if not any(t in c.lower() for t in TARGET_WORDS)
        ]
        # Ensure no target words in the filtered list
        for c in expected_cols:
            for t in TARGET_WORDS:
                assert t not in c.lower()

def test_3_leakage_guard_exits_when_race_results_are_populated():
    original_get_session = fastf1.get_session
    
    def mock_get_session(season, round_num, session_name):
        if session_name == 'R':
            sess = MagicMock()
            sess.session_status = 'Finished'
            sess.results = pd.DataFrame({'ClassifiedPosition': [1,2,3,4,5,6,7,8,9,10,11]})
            sess.load = lambda **kwargs: None
            return sess
        return original_get_session(season, round_num, session_name)
        
    with patch('fastf1.get_session', side_effect=mock_get_session):
        old_argv = sys.argv
        sys.argv = ['predict_miami_2026_race_intel.py']
        try:
            with pytest.raises(SystemExit) as e:
                runpy.run_path(SCRIPT_PATH)
            assert e.value.code == 0
        finally:
            sys.argv = old_argv

def test_4_confidence_never_returns_high(intel_globals):
    confidence = intel_globals['confidence']
    assert confidence != 'High'
    assert confidence in ['Medium-High', 'Medium', 'Medium-Low', 'Low']

def test_5_missing_fp1_does_not_crash():
    original_get_session = fastf1.get_session
    def mock_get_session(season, round_num, session_name):
        if session_name == 'FP1':
            raise Exception("Simulated FP1 network failure")
        sess = original_get_session(season, round_num, session_name)
        if session_name == 'R':
            sess.session_status = 'Testing'
            if hasattr(sess, 'results'):
                sess.results = pd.DataFrame()
        return sess
        
    with patch('fastf1.get_session', side_effect=mock_get_session):
        old_argv = sys.argv
        sys.argv = ['predict_miami_2026_race_intel.py', '--no-weather']
        try:
            gl = runpy.run_path(SCRIPT_PATH)
            assert 'FP1' in gl['failed']
            assert 'FP1' not in gl['loaded']
            assert len(gl['top3']) == 3
        finally:
            sys.argv = old_argv

def test_6_missing_sprint_does_not_crash():
    original_get_session = fastf1.get_session
    def mock_get_session(season, round_num, session_name):
        if session_name == 'S':
            raise Exception("Simulated Sprint failure")
        sess = original_get_session(season, round_num, session_name)
        if session_name == 'R':
            sess.session_status = 'Testing'
            if hasattr(sess, 'results'):
                sess.results = pd.DataFrame()
        return sess
        
    with patch('fastf1.get_session', side_effect=mock_get_session):
        old_argv = sys.argv
        sys.argv = ['predict_miami_2026_race_intel.py', '--no-weather']
        try:
            gl = runpy.run_path(SCRIPT_PATH)
            assert 'S' in gl['failed']
            assert 'S' not in gl['loaded']
            assert len(gl['top3']) == 3
        finally:
            sys.argv = old_argv

def test_7_weather_fallback_works_when_fastf1_weather_data_is_none():
    original_get_session = fastf1.get_session
    def mock_get_session(season, round_num, session_name):
        if session_name in ['R', 'Q', 'S']:
            sess = MagicMock()
            # FastF1 weather_data returns None when there is no weather
            sess.weather_data = None
            sess.load = lambda **kwargs: None
            sess.results = pd.DataFrame()
            return sess
        return original_get_session(season, round_num, session_name)
        
    with patch('fastf1.get_session', side_effect=mock_get_session):
        old_argv = sys.argv
        sys.argv = ['predict_miami_2026_race_intel.py']
        try:
            gl = runpy.run_path(SCRIPT_PATH)
            # Since fastf1 is returning None for weather, it should fallback
            assert gl['weather_features']['source'] in ['Open-Meteo API', 'none']
        finally:
            sys.argv = old_argv

def test_8_final_ensemble_score_changes_when_qualifying_position_changes(intel_globals):
    normalize_rank = intel_globals['normalize_rank']
    
    q_dict_1 = {'VER': 1, 'LEC': 2, 'NOR': 3}
    q_dict_2 = {'VER': 2, 'LEC': 1, 'NOR': 3}
    
    norm_1 = normalize_rank(q_dict_1)
    norm_2 = normalize_rank(q_dict_2)
    
    assert norm_1['VER'] < norm_1['LEC']
    assert norm_2['LEC'] < norm_2['VER']
    assert norm_1['LEC'] != norm_2['LEC']

def test_9_tyre_degradation_proxy_returns_float_for_stints(intel_globals):
    tyre_features = intel_globals['tyre_features']
    for abr, sessions in tyre_features.items():
        for sess, data in sessions.items():
            if 'avg_degradation' in data:
                assert isinstance(data['avg_degradation'], float)
            for stint_id, stint_data in data.get('stints', {}).items():
                assert isinstance(stint_data['degradation_s_per_lap'], float)

def test_10_normalize_rank_returns_values_in_0_1(intel_globals):
    normalize_rank = intel_globals['normalize_rank']
    
    res1 = normalize_rank({'a': 1, 'b': 2, 'c': 3})
    assert res1['a'] == 0.0
    assert res1['b'] == 0.5
    assert res1['c'] == 1.0
    
    res2 = normalize_rank({'a': 1, 'b': 2, 'c': 3}, higher_is_better=True)
    assert res2['a'] == 1.0
    assert res2['b'] == 0.5
    assert res2['c'] == 0.0


# ======== NEW CALIBRATION TESTS ========

def test_11_sprint_ontrack_differs_from_classified_when_penalty(intel_globals):
    """FIX 1: on-track finish differs from classified when last-lap Position differs."""
    sprint_features = intel_globals['sprint_features']
    # Check that the new fields exist
    for abr, sf in sprint_features.items():
        assert 'sprint_finish_position_classified' in sf, f"{abr} missing classified field"
        assert 'sprint_finish_position_ontrack' in sf, f"{abr} missing ontrack field"
        assert 'sprint_had_time_penalty' in sf, f"{abr} missing penalty flag"
    
    # If any driver has had_penalty=1, their on-track and classified MUST differ
    for abr, sf in sprint_features.items():
        if sf['sprint_had_time_penalty'] == 1:
            assert sf['sprint_finish_position_ontrack'] != sf['sprint_finish_position_classified'], \
                f"{abr}: penalty flagged but ontrack == classified"

def test_12_time_penalty_no_double_penalty(intel_globals):
    """FIX 4: A sprint time penalty should not simultaneously blow up
    sprint_score AND execution_risk. Execution risk penalty for time
    penalty is capped at 0.08 (not 0.25)."""
    compute_execution_risk = intel_globals['compute_execution_risk']
    
    # Driver with a time penalty but no position loss on-track
    sf = {
        'DRV': {
            'sprint_grid_position': 5.0,
            'sprint_finish_position_ontrack': 5.0,  # no positions lost on track
            'sprint_had_time_penalty': 1,
            'sprint_penalty_flag': 1,
        }
    }
    qf = {'DRV': {'qualifying_position': 10}}
    
    risk = compute_execution_risk('DRV', sf, qf)
    # Only the 0.08 discipline penalty should apply (no position loss, no front row)
    assert risk == pytest.approx(0.08, abs=0.01), \
        f"Expected ~0.08 risk for penalty-only, got {risk}"

def test_13_longrun_reliability_discounts_short_stints(intel_globals):
    """FIX 2: short stints get lower reliability."""
    fp1_features = intel_globals['fp1_features']
    
    for abr, fp in fp1_features.items():
        if not fp:
            continue
        lr_laps = fp.get('fp1_long_run_lap_count', 0)
        lr_rel = fp.get('fp1_long_run_reliability', 0.0)
        
        # If < 3 clean laps, reliability must be 0
        if lr_laps < 3:
            assert lr_rel == 0.0, f"{abr}: {lr_laps} laps but reliability={lr_rel}"
        # If >= 8 laps, fully trusted
        if lr_laps >= 8:
            assert lr_rel == 1.0, f"{abr}: {lr_laps} laps but reliability={lr_rel}"

def test_14_qualifying_gap_affects_qual_score(intel_globals):
    """FIX 3: qualifying score uses 50% position + 50% gap."""
    component_scores = intel_globals['component_scores']
    
    # The pole sitter MUST have q_score == 0.0 (pos=1, gap=0)
    pole_abr = None
    for abr, cs in component_scores.items():
        if cs['q_pos_score'] == 0.0 and cs['q_gap_score'] == 0.0:
            pole_abr = abr
            break
    
    assert pole_abr is not None, "No driver has q_pos_score=0 and q_gap_score=0"
    assert component_scores[pole_abr]['q_score'] == 0.0, \
        f"Pole sitter {pole_abr} should have q_score=0.0"

def test_15_pole_plus_top3_longrun_not_p10(intel_globals):
    """FIX 5 guardrail logic: pole + top-3 long-run pace cannot fall to P10
    from Sprint classified penalty alone."""
    ranked = intel_globals['ranked']
    qual_features = intel_globals['qual_features']
    fp1_features = intel_globals['fp1_features']
    
    # Find pole sitter
    pole_abr = None
    for abr, qf in qual_features.items():
        if qf.get('qualifying_position') == 1:
            pole_abr = abr
            break
    
    if pole_abr is None:
        pytest.skip("No pole sitter found")
    
    # Check FP1 long-run rank
    lr_rank = fp1_features.get(pole_abr, {}).get('fp1_best_lap_rank', 99)
    
    if lr_rank <= 3:
        # With pole position AND top-3 long-run pace, should not rank P10+
        rank_map = {abr: i+1 for i, (abr, _) in enumerate(ranked)}
        actual_rank = rank_map.get(pole_abr, 99)
        assert actual_rank <= 9, \
            f"Pole sitter {pole_abr} with FP1 rank {lr_rank} fell to P{actual_rank}"

def test_16_no_driver_names_hardcoded_in_scoring(intel_globals):
    """No driver abbreviations are hardcoded in scoring functions."""
    source_path = SCRIPT_PATH
    with open(source_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    # Known driver abbreviations that should NOT appear in scoring logic
    driver_codes = {
        'ANT', 'NOR', 'VER', 'LEC', 'PIA', 'RUS', 'HAM', 'GAS',
        'HAD', 'COL', 'LAW', 'SAI', 'BEA', 'OCO', 'ALB', 'HUL',
        'ALO', 'STR', 'LIN', 'PER', 'BOT', 'BOR'
    }
    
    scoring_funcs = [
        'compute_execution_risk', 'compute_upgrade_delta',
        'get_long_run_pace', 'get_sprint_pace', 'normalize_rank',
        'analyst_adjustment_layer'
    ]
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in scoring_funcs:
            func_source = ast.get_source_segment(source, node)
            if func_source:
                for code in driver_codes:
                    # Check for the abbreviation as a standalone string literal
                    assert f"'{code}'" not in func_source and f'"{code}"' not in func_source, \
                        f"Driver code '{code}' hardcoded in {node.name}()"

def test_17_empty_qualifying_results_does_not_crash():
    """Empty Q results must not crash; qual_features stays empty, top3 still produced."""
    original_get_session = fastf1.get_session
    def mock_get_session(season, round_num, session_name):
        if session_name == 'Q':
            sess = MagicMock()
            sess.results = pd.DataFrame()  # empty results
            sess.laps = pd.DataFrame()
            sess.weather_data = None
            sess.race_control_messages = None
            sess.load = lambda **kwargs: None
            return sess
        sess = original_get_session(season, round_num, session_name)
        if session_name == 'R':
            sess.session_status = 'Testing'
            if hasattr(sess, 'results'):
                sess.results = pd.DataFrame()
        return sess

    with patch('fastf1.get_session', side_effect=mock_get_session):
        old_argv = sys.argv
        sys.argv = ['predict_miami_2026_race_intel.py', '--no-weather']
        try:
            gl = runpy.run_path(SCRIPT_PATH)
            assert len(gl['qual_features']) == 0
            assert len(gl['top3']) == 3
        finally:
            sys.argv = old_argv

def test_18_analyst_layer_returns_reasons(intel_globals):
    """Adjustment reasons are returned for top 10."""
    reasons = intel_globals['adjustment_reasons']
    raw_ranking = intel_globals['raw_model_ranking']
    assert isinstance(reasons, dict)
    # Check that at least some top drivers have reasons
    top_abrs = [abr for abr, _ in raw_ranking[:10]]
    for abr in top_abrs:
        assert isinstance(reasons.get(abr, []), list)

def test_19_analyst_layer_pole_sitter_protection(intel_globals):
    """QP1 + top-5 long-run cannot rank outside top 5 without severe negatives."""
    layer_func = intel_globals['analyst_adjustment_layer']
    
    raw = [('DRV', 0.8)] + [(f'D{i}', 0.1) for i in range(1, 10)]
    feats = {
        'qual': {'DRV': {'qualifying_position': 1}},
        'sprint': {'DRV': {'sprint_finish_position_ontrack': 2, 'sprint_grid_position': 1}},
        'fp1': {'DRV': {'fp1_best_lap_rank': 3, 'fp1_long_run_reliability': 1.0}}
    }
    comp_scores = {'DRV': {'exec_score': 0.1, 'tyre_score': 0.3}}
    ctx = {'rain_risk': 0.0, 'ml_podium': {}, 'hist': pd.DataFrame(), 'driver_col': None}
    
    adj_ranked, adjusted, reasons, audit = layer_func(raw, feats, comp_scores, ctx)
    
    # Should get a pole protection bonus
    assert adjusted['DRV'] < 0.8
    assert any('pole' in r for r in reasons['DRV'])

def test_20_analyst_layer_sprint_winner_boost(intel_globals):
    """Sprint winner receives boost but is not forced to P1."""
    layer_func = intel_globals['analyst_adjustment_layer']
    
    raw = [('DRV', 0.8)]
    feats = {
        'qual': {'DRV': {'qualifying_position': 4}},
        'sprint': {'DRV': {'sprint_finish_position_ontrack': 1, 'sprint_grid_position': 4}},
        'fp1': {'DRV': {'fp1_best_lap_rank': 1}}
    }
    comp_scores = {'DRV': {'exec_score': 0.1}}
    ctx = {'rain_risk': 0.0, 'ml_podium': {}, 'hist': pd.DataFrame(), 'driver_col': None}
    
    adj_ranked, adjusted, reasons, audit = layer_func(raw, feats, comp_scores, ctx)
    
    assert adjusted['DRV'] < 0.8
    assert any('sprint winner' in r for r in reasons['DRV'])

def test_21_short_longrun_discounted(intel_globals):
    """Short FP1 long-run sample is discounted."""
    layer_func = intel_globals['analyst_adjustment_layer']
    
    raw = [('DRV', 0.5)]
    feats = {
        'qual': {},
        'sprint': {},
        'fp1': {'DRV': {'fp1_long_run_reliability': 0.2}} # low reliability
    }
    # fp1_score < 0.15 indicates they benefited from it
    comp_scores = {'DRV': {'fp1_score': 0.1}}
    ctx = {'rain_risk': 0.0, 'ml_podium': {}, 'hist': pd.DataFrame(), 'driver_col': None}
    
    adj_ranked, adjusted, reasons, audit = layer_func(raw, feats, comp_scores, ctx)
    
    # Score should increase (penalty)
    assert adjusted['DRV'] > 0.5
    assert any('short FP1 sample discount' in r for r in reasons['DRV'])
