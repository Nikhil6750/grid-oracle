import React, { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = 'http://127.0.0.1:8000';
const WS_BASE = 'ws://127.0.0.1:8000';

const COMPOUND_NAMES = { 1: 'SOFT', 2: 'MEDIUM', 3: 'HARD', 4: 'INTER', 5: 'WET' };
const COMPOUND_COLORS = {
  1: '#e63946', // soft - red
  2: '#f4c542', // medium - yellow
  3: '#e8e1d2', // hard - white/light
  4: '#43aa8b', // inter - green
  5: '#277da1', // wet - blue
};

function CompoundPill({ code, life }) {
  const c = Math.round(code);
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
      <span style={{
        display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%',
        background: COMPOUND_COLORS[c] || 'var(--ink-3)', border: '1px solid var(--ink-3)',
      }} />
      <span style={{ color: 'var(--ink-2)' }}>{COMPOUND_NAMES[c] || '—'}</span>
      <span style={{ color: 'var(--ink-3)', fontSize: '10px' }}>L{Math.round(life)}</span>
    </span>
  );
}

function ProbBar({ value }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ flex: 1, height: '6px', background: 'var(--paper-3)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: 'var(--aston)', transition: 'width 0.6s ease' }} />
      </div>
      <span style={{ width: '38px', textAlign: 'right', color: 'var(--ink-2)', fontSize: '11px' }}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

function LivePrediction({ season = '2026', round = '6' }) {
  const [snapshot, setSnapshot] = useState(null);
  const [connected, setConnected] = useState(false);
  const [usingRest, setUsingRest] = useState(false);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const reconnectRef = useRef(null);
  const restTimerRef = useRef(null);
  const mountedRef = useRef(true);

  // --- REST fallback ------------------------------------------------------ //
  const fetchRest = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/live/current/${season}/${round}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (!mountedRef.current) return;
      if (data.type === 'error') {
        setError(data.message || 'No data available');
      } else {
        setSnapshot(data);
        setError(null);
      }
      setUsingRest(true);
    } catch (e) {
      if (mountedRef.current) setError('Backend offline — prediction unavailable.');
    }
  }, [season, round]);

  const startRestPolling = useCallback(() => {
    if (restTimerRef.current) return;
    fetchRest();
    restTimerRef.current = setInterval(fetchRest, 30000);
  }, [fetchRest]);

  const stopRestPolling = useCallback(() => {
    if (restTimerRef.current) {
      clearInterval(restTimerRef.current);
      restTimerRef.current = null;
    }
  }, []);

  // --- WebSocket with auto-reconnect ------------------------------------- //
  const connect = useCallback(() => {
    let ws;
    try {
      ws = new WebSocket(`${WS_BASE}/ws/live/${season}/${round}`);
    } catch {
      startRestPolling();
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnected(true);
      setUsingRest(false);
      setError(null);
      stopRestPolling();
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'prediction') {
          setSnapshot(data);
          setError(null);
        } else if (data.type === 'error') {
          setError(data.message || 'No data available');
        }
      } catch { /* ignore malformed frames */ }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      // Fall back to REST and schedule a reconnect attempt.
      startRestPolling();
      reconnectRef.current = setTimeout(connect, 5000);
    };

    ws.onerror = () => {
      try { ws.close(); } catch { /* noop */ }
    };
  }, [season, round, startRestPolling, stopRestPolling]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      stopRestPolling();
      if (wsRef.current) {
        try { wsRef.current.close(); } catch { /* noop */ }
      }
    };
  }, [connect, stopRestPolling]);

  const drivers = snapshot?.drivers || [];
  const isLive = snapshot?.mode === 'LIVE';
  const badge = !connected && !usingRest
    ? { label: 'OFFLINE', color: 'var(--ink-3)' }
    : isLive
      ? { label: 'LIVE', color: 'var(--gold)' }
      : { label: 'REPLAY', color: 'var(--aston)' };

  return (
    <section className="pred-panel">
      <div className="pred-panel-inner">
        <div className="pred-head">
          <h2 className="pred-title">LIVE <em>&mdash; RACE PREDICTION</em></h2>
          <div className="pred-status">
            <span className="pred-dot" style={{
              background: badge.color,
              animation: isLive && connected ? 'pulseDot 1.4s infinite' : 'none',
            }} />
            {badge.label}
            {snapshot && (
              <span style={{ marginLeft: '10px', color: 'var(--ink-3)' }}>
                LAP {snapshot.lap_n}/{snapshot.total_laps}
              </span>
            )}
          </div>
        </div>

        {error && !drivers.length && (
          <div style={{ color: 'var(--ink-3)', fontFamily: "'Inter', sans-serif", fontSize: '13px', padding: '20px 0' }}>
            {error}
          </div>
        )}

        {!error && !drivers.length && (
          <div className="pred-result">
            <div className="skeleton-box" style={{ width: '60%' }} />
            <div className="skeleton-box" style={{ width: '80%' }} />
            <div className="skeleton-box" style={{ width: '40%' }} />
          </div>
        )}

        {drivers.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--rule-light)', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  <th style={{ padding: '8px 12px', textAlign: 'left', width: '52px' }}>Pred</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', width: '44px' }}>Now</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left' }}>Driver</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', width: '160px' }}>Win Probability</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left' }}>Tyre</th>
                  <th style={{ padding: '8px 12px', textAlign: 'right', width: '48px' }}>Pits</th>
                </tr>
              </thead>
              <tbody>
                {drivers.map((d, i) => {
                  const delta = (d.current_position ?? 0) - d.predicted_position;
                  return (
                    <tr key={d.driver_code} style={{
                      borderBottom: '1px solid var(--rule-light)',
                      background: i === 0 ? 'rgba(204,30,30,0.06)' : i < 3 ? 'rgba(34,153,113,0.04)' : 'transparent',
                    }}>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{
                          display: 'inline-block', width: '24px', height: '24px', lineHeight: '24px',
                          textAlign: 'center', fontSize: '11px', fontWeight: 700,
                          background: i === 0 ? 'var(--gold)' : i < 3 ? 'var(--aston)' : 'var(--paper)',
                          color: i < 3 ? '#fff' : 'var(--ink-2)',
                          border: i >= 3 ? '1px solid var(--rule-light)' : 'none',
                        }}>{d.predicted_position}</span>
                      </td>
                      <td style={{ padding: '10px 12px', color: 'var(--ink-3)' }}>
                        {d.current_position ?? '—'}
                        {delta !== 0 && (
                          <span style={{ marginLeft: '4px', fontSize: '10px', color: delta > 0 ? 'var(--aston)' : 'var(--gold)' }}>
                            {delta > 0 ? `▲${delta}` : `▼${Math.abs(delta)}`}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '10px 12px', fontWeight: 700, color: 'var(--ink)' }}>{d.driver_code}</td>
                      <td style={{ padding: '10px 12px' }}><ProbBar value={d.win_probability} /></td>
                      <td style={{ padding: '10px 12px' }}>
                        <CompoundPill code={d.tyre_compound} life={d.tyre_life} />
                      </td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--ink-2)' }}>
                        {Math.round(d.pit_stops_done)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ marginTop: '12px', fontSize: '11px', color: 'var(--ink-3)', fontFamily: "'Inter', sans-serif" }}>
          {snapshot?.event_name ? `${snapshot.event_name} · ` : ''}
          Predicted final positions update every 30s
          {usingRest && !connected ? ' · REST fallback' : ''}
        </div>
      </div>
    </section>
  );
}

export default LivePrediction;
