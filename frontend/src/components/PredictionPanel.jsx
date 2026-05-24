import React, { useState, useEffect } from 'react';
import { checkHealth, getRacePrediction } from '../services/api';

function PredictionPanel() {
  const [status, setStatus] = useState('checking');
  const [season, setSeason] = useState('2026');
  const [round, setRound] = useState('5');
  const [stage, setStage] = useState('post_qualifying');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
    checkHealth().then(ok => {
      setStatus(ok ? 'connected' : 'offline');
      if (ok) {
        setLoading(true);
        getRacePrediction({ season: '2026', round: '5', stage: 'post_qualifying' })
          .then(data => setResult(data))
          .catch(err => setError(err.message))
          .finally(() => setLoading(false));
      }
    });
  }, []);

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setShowRaw(false);
    
    try {
      const data = await getRacePrediction({ season, round, stage });
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch prediction.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="pred-panel">
      <div className="pred-panel-inner">
        <div className="pred-head">
          <h2 className="pred-title">GRID ORACLE <em>— CANADIAN GP PREDICTION</em></h2>
          <div className="pred-status">
            <span className="pred-dot" style={{ background: status === 'connected' ? 'var(--aston)' : 'var(--racing)' }}></span>
            {status}
          </div>
        </div>

        <div className="pred-controls" style={{ display: 'none' }}>
          <select 
            className="pred-select" 
            value={season} 
            onChange={e => setSeason(e.target.value)}
          >
            <option value="2024">2024</option>
            <option value="2025">2025</option>
            <option value="2026">2026</option>
          </select>
          <input 
            type="number" 
            className="pred-input" 
            value={round} 
            onChange={e => setRound(e.target.value)} 
            placeholder="Round" 
            style={{ width: '90px' }}
          />
          <select 
            className="pred-select" 
            value={stage} 
            onChange={e => setStage(e.target.value)}
          >
            <option value="pre_weekend">Pre-Weekend Analysis</option>
            <option value="post_qualifying">Post-Qualifying Prediction</option>
          </select>
          <button 
            className="pred-btn" 
            onClick={handlePredict} 
            disabled={loading || status === 'offline'}
          >
            {loading ? 'Running...' : 'Run Prediction'}
          </button>
        </div>

        {error && (
          <div style={{ color: 'var(--racing)', fontFamily: "'Inter', sans-serif", fontSize: '13px', marginBottom: '20px' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading && (
          <div className="pred-result">
            <div className="skeleton-box" style={{ width: '40%' }}></div>
            <div className="skeleton-box" style={{ width: '70%' }}></div>
            <div className="skeleton-box" style={{ width: '50%' }}></div>
          </div>
        )}

        {result && !loading && (
          <div className="pred-result">
            <div className="pred-meta-grid">
              <div className="pred-meta-card" style={{ display: 'none' }}>
                <div className="pred-meta-label">Pole Sitter</div>
                <div className="pred-meta-val">{result.pole_sitter_candidate || 'TBD'}</div>
              </div>
              <div className="pred-meta-card">
                <div className="pred-meta-label">Race Winner Candidate</div>
                <div className="pred-meta-val">{result.race_winner_candidate || (result.podium_ranking && result.podium_ranking.length > 0 && result.podium_ranking[0].driver) || 'TBD'}</div>
              </div>
              <div className="pred-meta-card" style={{ display: 'none' }}>
                <div className="pred-meta-label">Models Used</div>
                <div className="pred-meta-val" style={{ fontSize: '14px', fontFamily: "'JetBrains Mono', monospace" }}>
                  {result.models_used ? Object.entries(result.models_used).filter(([, v]) => v != null).map(([k, v]) => `${k.replace('_', ' ')}: ${v}`).join(' | ') : 'Ensemble'}
                </div>
              </div>
            </div>

            <div className="podium-block" style={{ padding: '0 0 24px', border: 'none' }}>
              <div className="podium-head">Predicted Podium</div>
              <div style={{ fontSize: '11px', color: 'var(--ink-3)', fontFamily: "'Inter', sans-serif", marginBottom: '12px' }}>
                Based on qualifying data · Post-Qualifying Stage · 2026 Canadian GP
              </div>
              <div className="podium-list">
                {result.podium_ranking && result.podium_ranking.slice(0,3).map((entry, i) => (
                  <div key={i} className={`pod-row p${i+1}`}>
                    <div className="pod-badge">P{i+1}</div>
                    <div>
                      <div className="pod-driver-name">
                        {entry.driver} <span style={{ fontSize: '11px', color: 'var(--ink-3)', marginLeft: '8px' }}>{(entry.probability * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {result.top10_ranking && result.top10_ranking.length > 0 && (
              <div style={{ marginBottom: '24px' }}>
                <div className="podium-head">Points Finishers (Not Race Order)</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '8px' }}>
                  {result.top10_ranking.map((entry, i) => (
                    <div key={i} style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', padding: '8px', background: 'var(--paper)', border: '1px solid var(--rule-light)' }}>
                      <span style={{ color: 'var(--ink-3)', marginRight: '8px' }}>{String(i+1).padStart(2, '0')}</span>
                      <strong>{entry.driver}</strong> <span style={{ color: 'var(--ink-3)', float: 'right' }}>{(entry.probability * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.warnings && result.warnings.length > 0 && (
              <div style={{ display: 'none', background: 'rgba(212,160,23,0.1)', borderLeft: '2px solid var(--gold)', padding: '12px 16px', marginBottom: '24px', fontFamily: "'Inter', sans-serif", fontSize: '12px', color: 'var(--ink-2)' }}>
                <strong>Warnings:</strong> {result.warnings.join(' | ')}
              </div>
            )}

            <button className="pred-raw-toggle" onClick={() => setShowRaw(!showRaw)}>
              <span>Raw JSON Data</span>
              <span>{showRaw ? '−' : '+'}</span>
            </button>
            {showRaw && (
              <div className="pred-raw-content">
                {JSON.stringify(result, null, 2)}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default PredictionPanel;
