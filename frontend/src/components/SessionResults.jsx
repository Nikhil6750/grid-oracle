import React, { useState, useEffect } from 'react';

const JOLPI = 'https://api.jolpi.ca/ergast/f1';

async function fetchQualifying(season, round) {
  try {
    const res = await fetch(`${JOLPI}/${season}/${round}/qualifying.json`);
    const data = await res.json();
    const race = data.MRData.RaceTable.Races[0];
    if (!race || !race.QualifyingResults) return null;
    return {
      type: 'Qualifying',
      raceName: race.raceName,
      results: race.QualifyingResults.slice(0, 10).map(r => ({
        position: r.position,
        driver: r.Driver.code,
        name: `${r.Driver.givenName.charAt(0)}. ${r.Driver.familyName}`,
        team: r.Constructor.name,
        q1: r.Q1 || 'â€”',
        q2: r.Q2 || 'â€”',
        q3: r.Q3 || 'â€”',
        bestTime: r.Q3 || r.Q2 || r.Q1 || 'â€”',
      }))
    };
  } catch { return null; }
}

async function fetchRaceResult(season, round) {
  try {
    const res = await fetch(`${JOLPI}/${season}/${round}/results.json`);
    const data = await res.json();
    const race = data.MRData.RaceTable.Races[0];
    if (!race || !race.Results) return null;
    return {
      type: 'Race Result',
      raceName: race.raceName,
      results: race.Results.slice(0, 10).map(r => ({
        position: r.position,
        driver: r.Driver.code,
        name: `${r.Driver.givenName.charAt(0)}. ${r.Driver.familyName}`,
        team: r.Constructor.name,
        time: r.Time?.time || r.status,
        points: r.points,
        fastestLap: r.FastestLap?.rank === '1',
      }))
    };
  } catch { return null; }
}

function SessionResults({ season = '2026', round = '6' }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('qualifying');

  useEffect(() => {
    async function load() {
      setLoading(true);
      // Try race result first, then qualifying
      const race = await fetchRaceResult(season, round);
      if (race) {
        setSession(race);
        setActiveTab('race');
      } else {
        const quali = await fetchQualifying(season, round);
        setSession(quali);
        setActiveTab('qualifying');
      }
      setLoading(false);
    }
    load();
  }, [season, round]);

  if (loading) return (
    <section className="pred-panel">
      <div className="pred-panel-inner">
        <div className="pred-head">
          <h2 className="pred-title">SESSION <em>â€” RESULTS</em></h2>
        </div>
        <div className="pred-result">
          <div className="skeleton-box" style={{ width: '60%' }}></div>
          <div className="skeleton-box" style={{ width: '80%' }}></div>
          <div className="skeleton-box" style={{ width: '40%' }}></div>
        </div>
      </div>
    </section>
  );

  if (!session) return (
    <section className="pred-panel">
      <div className="pred-panel-inner">
        <div className="pred-head">
          <h2 className="pred-title">SESSION <em>â€” RESULTS</em></h2>
        </div>
        <div style={{ color: 'var(--ink-3)', fontFamily: "'Inter', sans-serif", fontSize: '13px', padding: '20px 0' }}>
          No session results available yet. Check back after qualifying.
        </div>
      </div>
    </section>
  );

  return (
    <section className="pred-panel">
      <div className="pred-panel-inner">
        <div className="pred-head">
          <h2 className="pred-title">SESSION <em>&mdash; {session.type.toUpperCase()}</em></h2>
          <div className="pred-status">
            <span className="pred-dot" style={{ background: 'var(--aston)' }}></span>
            {session.raceName}
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--rule-light)', color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <th style={{ padding: '8px 12px', textAlign: 'left', width: '40px' }}>P</th>
                <th style={{ padding: '8px 12px', textAlign: 'left' }}>Driver</th>
                <th style={{ padding: '8px 12px', textAlign: 'left' }}>Team</th>
                {session.type === 'Qualifying' ? (
                  <>
                    <th style={{ padding: '8px 12px', textAlign: 'right' }}>Q1</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right' }}>Q2</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right' }}>Q3</th>
                  </>
                ) : (
                  <>
                    <th style={{ padding: '8px 12px', textAlign: 'right' }}>Time/Gap</th>
                    <th style={{ padding: '8px 12px', textAlign: 'right' }}>Pts</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {session.results.map((r, i) => (
                <tr key={i} style={{
                  borderBottom: '1px solid var(--rule-light)',
                  background: i === 0 ? 'rgba(212,160,23,0.06)' : i === 1 ? 'rgba(180,180,180,0.04)' : i === 2 ? 'rgba(180,100,0,0.04)' : 'transparent'
                }}>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{
                      display: 'inline-block', width: '24px', height: '24px', lineHeight: '24px',
                      textAlign: 'center', fontSize: '11px', fontWeight: 700,
                      background: i === 0 ? 'var(--gold)' : i === 1 ? '#aaa' : i === 2 ? '#cd7f32' : 'var(--paper)',
                      color: i < 3 ? '#000' : 'var(--ink-2)',
                      border: i >= 3 ? '1px solid var(--rule-light)' : 'none'
                    }}>{r.position}</span>
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <div style={{ fontWeight: 700, color: 'var(--ink-1)' }}>{r.name}</div>
                    <div style={{ fontSize: '10px', color: 'var(--ink-3)', marginTop: '2px' }}>{r.driver}</div>
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--ink-2)', fontSize: '11px' }}>{r.team}</td>
                  {session.type === 'Qualifying' ? (
                    <>
                      <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--ink-3)' }}>{r.q1}</td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--ink-3)' }}>{r.q2}</td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', color: i === 0 ? 'var(--aston)' : 'var(--ink-1)', fontWeight: i === 0 ? 700 : 400 }}>{r.q3}</td>
                    </>
                  ) : (
                    <>
                      <td style={{ padding: '10px 12px', textAlign: 'right', color: i === 0 ? 'var(--aston)' : 'var(--ink-2)' }}>{r.time}</td>
                      <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 700 }}>{r.points}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ marginTop: '12px', fontSize: '11px', color: 'var(--ink-3)', fontFamily: "'Inter', sans-serif" }}>
          Data via Jolpica F1 API Â· Refresh page for latest results
        </div>
      </div>
    </section>
  );
}

export default SessionResults;
