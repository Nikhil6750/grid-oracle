import React from 'react';

const MOCK_CONTEXT = {
  raceName: "MONACO GP",
  round: "Round 6",
  circuit: "Circuit de Monaco",
  date: "Jun 06"
};

const MOCK_RESULTS = [
  { pos: 1, driver: 'ANT', team: 'Mercedes', q1: '1:12.890', q2: '1:12.330', q3: '1:12.051', teamId: 'mercedes' },
  { pos: 2, driver: 'VER', team: 'Red Bull', q1: '1:12.910', q2: '1:12.440', q3: '1:12.094', teamId: 'redbull' },
  { pos: 3, driver: 'HAM', team: 'Ferrari', q1: '1:13.110', q2: '1:12.600', q3: '1:12.279', teamId: 'ferrari' },
  { pos: 4, driver: 'LEC', team: 'Ferrari', q1: '1:13.050', q2: '1:12.550', q3: '1:12.351', teamId: 'ferrari' },
  { pos: 5, driver: 'HAD', team: 'Red Bull', q1: '1:13.200', q2: '1:12.700', q3: '1:12.434', teamId: 'redbull' },
  { pos: 6, driver: 'RUS', team: 'Mercedes', q1: '1:13.150', q2: '1:12.650', q3: '1:12.445', teamId: 'mercedes' },
  { pos: 7, driver: 'PIA', team: 'McLaren', q1: '1:13.300', q2: '1:12.800', q3: '1:12.624', teamId: 'mclaren' },
  { pos: 8, driver: 'NOR', team: 'McLaren', q1: '1:13.250', q2: '1:12.750', q3: '1:12.765', teamId: 'mclaren' },
  { pos: 9, driver: 'GAS', team: 'Alpine', q1: '1:13.500', q2: '1:13.100', q3: '1:13.226', teamId: 'alpine' },
  { pos: 10, driver: 'LAW', team: 'RB', q1: '1:13.600', q2: '1:13.300', q3: '1:13.412', teamId: 'rb' },
];

export default function SessionResults() {
  return (
    <section className="session-results reveal">
      <div className="sr-header">
        <h3 className="sr-title">{MOCK_CONTEXT.raceName} — QUALIFYING RESULTS</h3>
        <p className="sr-sub">{MOCK_CONTEXT.round} · {MOCK_CONTEXT.circuit} · {MOCK_CONTEXT.date}</p>
      </div>
      
      <div className="sr-table-container">
        <table className="sr-table">
          <thead>
            <tr>
              <th>P</th>
              <th>DRIVER</th>
              <th>TEAM</th>
              <th>Q1</th>
              <th>Q2</th>
              <th>Q3</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_RESULTS.map((row, i) => {
              let accentClass = '';
              if (row.pos === 1) accentClass = 'sr-p1';
              else if (row.pos === 2) accentClass = 'sr-p2';
              else if (row.pos === 3) accentClass = 'sr-p3';

              return (
                <tr key={i} className={`sr-row ${accentClass}`}>
                  <td className="sr-pos">{row.pos}</td>
                  <td className="sr-driver">
                    <span className={`sr-team-dot bg-${row.teamId}`}></span>
                    {row.driver}
                  </td>
                  <td className="sr-team">{row.team}</td>
                  <td className="sr-time dim">{row.q1}</td>
                  <td className="sr-time dim">{row.q2}</td>
                  <td className={`sr-time q3 ${row.pos <= 3 ? 'gold-tinge' : ''}`}>{row.q3}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <style jsx>{`
        .session-results {
          width: 100%;
          margin-top: 60px;
        }
        .sr-header {
          margin-bottom: 24px;
        }
        .sr-title {
          font-family: var(--font-display);
          font-size: clamp(32px, 5vw, 48px);
          color: var(--white);
          margin-bottom: 8px;
          line-height: 1;
        }
        .sr-sub {
          font-family: var(--font-mono);
          font-size: 11px;
          color: rgba(255,255,255,0.4);
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }
        .sr-table-container {
          width: 100%;
          overflow-x: auto;
        }
        .sr-table {
          width: 100%;
          border-collapse: collapse;
          text-align: left;
        }
        .sr-table th {
          font-family: var(--font-mono);
          font-size: 9px;
          letter-spacing: 0.2em;
          color: rgba(255,255,255,0.4);
          border-bottom: 1px solid rgba(255,255,255,0.08);
          padding: 0 0 12px 0;
          font-weight: normal;
        }
        .sr-row {
          border-bottom: 1px solid rgba(255,255,255,0.05);
          border-left: 3px solid transparent;
          transition: background 0.2s, border-left-color 0.2s;
        }
        .sr-row:hover {
          background: rgba(225,6,0,0.04);
          border-left: 3px solid var(--red);
        }
        .sr-p1 { border-left: 3px solid var(--team-gold); }
        .sr-p2 { border-left: 3px solid var(--team-silver); }
        .sr-p3 { border-left: 3px solid var(--team-bronze); }
        
        .sr-row td {
          padding: 14px 0;
        }
        .sr-row td:first-child {
          padding-left: 12px;
        }
        
        .sr-pos {
          font-family: var(--font-mono);
          font-size: 11px;
          color: rgba(255,255,255,0.5);
        }
        .sr-driver {
          display: flex;
          align-items: center;
          gap: 12px;
          font-family: var(--font-display);
          font-size: 18px;
          color: var(--white);
          letter-spacing: 0.05em;
        }
        .sr-team-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }
        .sr-team {
          font-family: var(--font-body);
          font-size: 13px;
          color: rgba(255,255,255,0.5);
        }
        .sr-time {
          font-family: var(--font-mono);
          font-size: 12px;
        }
        .sr-time.dim {
          color: rgba(255,255,255,0.4);
        }
        .sr-time.q3 {
          color: var(--white);
          font-weight: bold;
        }
        .sr-time.gold-tinge {
          color: #f7e8b6;
        }
      `}</style>
    </section>
  );
}
