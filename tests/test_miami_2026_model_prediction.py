import os
import sys
import json
import pytest
import pandas as pd
import numpy as np
import unittest.mock
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))
import predict_miami_2026_model

def test_1_script_imports():
    """test_1: Script imports without errors"""
    assert 'predict_miami_2026_model' in sys.modules

@patch('fastf1.get_session')
@patch('fastf1.get_event_schedule')
@patch('joblib.load')
@patch('os.path.exists')
@patch('pandas.read_parquet')
def test_2_median_fill(mock_read_parquet, mock_exists, mock_joblib, mock_schedule, mock_session):
    """test_2: Median fill works when driver has no history"""
    mock_schedule.return_value = pd.DataFrame({'EventName': ['Miami Grand Prix'], 'RoundNumber': [5]})
    mock_sess = MagicMock()
    mock_sess.results = pd.DataFrame({
        'DriverNumber': ['1', '16'], 'Abbreviation': ['VER', 'LEC'],
        'FullName': ['Max Verstappen', 'Charles Leclerc'], 'TeamName': ['Red Bull', 'Ferrari'],
        'Position': [1, 2], 'Q3': pd.to_timedelta([60, 61], unit='s')
    })
    mock_session.return_value = mock_sess
    mock_read_parquet.return_value = pd.DataFrame()
    mock_exists.return_value = True
    
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1, 2])
    mock_model.predict_proba.return_value = np.array([[0.1, 0.9], [0.2, 0.8]])
    mock_joblib.return_value = mock_model
    
    with patch('builtins.open', unittest.mock.mock_open(read_data='{"race_finish_advanced_post_qualifying": ["rolling_avg_finish_5"]}')):
        with patch('json.dump') as mock_json_dump:
            with patch('sys.argv', ['predict_miami_2026_model.py']):
                predict_miami_2026_model.main()
                args, _ = mock_json_dump.call_args
                out = args[0]
                assert len(out['top3']) > 0

def test_3_no_target_columns():
    """test_3: Inference dataframe has no target columns"""
    cols = ['feature_1', 'target_variable', 'race_result', 'finish_position', 'podium_actual', 'good_col']
    exclude_keywords = ['target', 'finish_position', 'race_result', 'final_position', 'winner', 'podium_actual']
    filtered = [c for c in cols if not any(k in c for k in exclude_keywords)]
    assert 'target_variable' not in filtered
    assert 'race_result' not in filtered
    assert 'finish_position' not in filtered
    assert 'podium_actual' not in filtered
    assert 'good_col' in filtered

@patch('fastf1.get_session')
@patch('fastf1.get_event_schedule')
@patch('joblib.load')
@patch('os.path.exists')
@patch('pandas.read_parquet')
def test_4_top3_output(mock_read_parquet, mock_exists, mock_joblib, mock_schedule, mock_session):
    """test_4: Top3 output has exactly 3 entries with positions 1,2,3"""
    mock_schedule.return_value = pd.DataFrame({'EventName': ['Miami Grand Prix'], 'RoundNumber': [5]})
    mock_sess = MagicMock()
    mock_sess.results = pd.DataFrame({
        'DriverNumber': ['1', '16', '4', '81'], 'Abbreviation': ['VER', 'LEC', 'NOR', 'PIA'],
        'FullName': ['V', 'L', 'N', 'P'], 'TeamName': ['R', 'F', 'M', 'M'],
        'Position': [1, 2, 3, 4], 'Q3': pd.to_timedelta([60, 61, 62, 63], unit='s')
    })
    mock_session.return_value = mock_sess
    mock_read_parquet.return_value = pd.DataFrame()
    mock_exists.return_value = True
    
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1, 2, 3, 4])
    mock_model.predict_proba.return_value = np.array([[0.1, 0.9], [0.2, 0.8], [0.3, 0.7], [0.4, 0.6]])
    mock_joblib.return_value = mock_model
    
    with patch('builtins.open', unittest.mock.mock_open(read_data='{}')):
        with patch('json.dump') as mock_json_dump:
            with patch('sys.argv', ['predict_miami_2026_model.py']):
                predict_miami_2026_model.main()
                args, _ = mock_json_dump.call_args
                out = args[0]
                assert len(out['top3']) == 3
                assert [t['position'] for t in out['top3']] == [1, 2, 3]

@patch('fastf1.get_session')
@patch('fastf1.get_event_schedule')
@patch('joblib.load')
@patch('os.path.exists')
@patch('pandas.read_parquet')
def test_5_final_score_in_range(mock_read_parquet, mock_exists, mock_joblib, mock_schedule, mock_session):
    """test_5: final_score is in [0, 1] for all drivers"""
    mock_schedule.return_value = pd.DataFrame({'EventName': ['Miami Grand Prix'], 'RoundNumber': [5]})
    mock_sess = MagicMock()
    mock_sess.results = pd.DataFrame({
        'DriverNumber': ['1', '16'], 'Abbreviation': ['VER', 'LEC'],
        'FullName': ['V', 'L'], 'TeamName': ['R', 'F'],
        'Position': [1, 2], 'Q3': pd.to_timedelta([60, 61], unit='s')
    })
    mock_session.return_value = mock_sess
    mock_read_parquet.return_value = pd.DataFrame()
    mock_exists.return_value = True
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1, 2])
    mock_model.predict_proba.return_value = np.array([[0.1, 0.9], [0.2, 0.8]])
    mock_joblib.return_value = mock_model
    
    with patch('builtins.open', unittest.mock.mock_open(read_data='{}')):
        with patch('json.dump') as mock_json_dump:
            with patch('sys.argv', ['predict_miami_2026_model.py']):
                predict_miami_2026_model.main()
                args, _ = mock_json_dump.call_args
                out = args[0]
                for t in out['full_table']:
                    assert 0 <= t['final_score'] <= 1

@patch('fastf1.get_session')
@patch('fastf1.get_event_schedule')
def test_6_all_sessions_fail(mock_schedule, mock_session):
    """test_6: Script handles all sessions failing gracefully"""
    mock_schedule.return_value = pd.DataFrame({'EventName': ['Miami Grand Prix'], 'RoundNumber': [5]})
    mock_session.side_effect = Exception("No connection")
    
    with patch('sys.argv', ['predict_miami_2026_model.py']):
        with pytest.raises(SystemExit) as excinfo:
            predict_miami_2026_model.main()
        assert excinfo.value.code == 1

@patch('fastf1.get_session')
@patch('fastf1.get_event_schedule')
@patch('joblib.load')
@patch('os.path.exists')
@patch('pandas.read_parquet')
def test_7_qualifying_position_exists(mock_read_parquet, mock_exists, mock_joblib, mock_schedule, mock_session):
    """test_7: qualifying_position column exists and has no NaN after matrix construction"""
    mock_schedule.return_value = pd.DataFrame({'EventName': ['Miami Grand Prix'], 'RoundNumber': [5]})
    mock_sess = MagicMock()
    mock_sess.results = pd.DataFrame({
        'DriverNumber': ['1', '16'], 'Abbreviation': ['VER', 'LEC'],
        'FullName': ['V', 'L'], 'TeamName': ['R', 'F'],
        'Position': [1, 2], 'Q3': pd.to_timedelta([60, 61], unit='s')
    })
    mock_session.return_value = mock_sess
    mock_read_parquet.return_value = pd.DataFrame()
    mock_exists.return_value = True
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1, 2])
    mock_model.predict_proba.return_value = np.array([[0.1, 0.9], [0.2, 0.8]])
    mock_joblib.return_value = mock_model
    
    with patch('builtins.open', unittest.mock.mock_open(read_data='{}')):
        with patch('json.dump') as mock_json_dump:
            with patch('sys.argv', ['predict_miami_2026_model.py']):
                predict_miami_2026_model.main()
                args, _ = mock_json_dump.call_args
                out = args[0]
                for t in out['top3']:
                    assert 'qualifying_position' in t
                    assert t['qualifying_position'] is not None
