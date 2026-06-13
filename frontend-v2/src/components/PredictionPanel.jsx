import React from 'react';

// TODO: replace with live API
const PREDICTIONS = [
  { pos: 'P2', code: 'HAM', name: 'HAMILTON', team: 'FERRARI', teamClass: 'team-ferrari', bgClass: 'bg-ferrari', prob: 76, accent: 'var(--team-silver)', height: '90%' },
  { pos: 'P1', code: 'ANT', name: 'ANTONELLI', team: 'MERCEDES', teamClass: 'team-mercedes', bgClass: 'bg-mercedes', prob: 87, accent: 'var(--team-gold)', height: '100%' },
  { pos: 'P3', code: 'VER', name: 'VERSTAPPEN', team: 'RED BULL', teamClass: 'team-redbull', bgClass: 'bg-redbull', prob: 64, accent: 'var(--team-bronze)', height: '85%' },
];

export default function PredictionPanel() {
  return (
    <section className="pred-section reveal">
      
      {/* Top Bar */}
      <div className="pred-topbar">
        <div className="pt-left">§ 04 · GRID ORACLE</div>
        <div className="pt-center">BARCELONA GP PREDICTION</div>
        <div className="pt-right">
          <div className="conn-dot"></div> CONNECTED
        </div>
      </div>

      {/* Podium Cards */}
      <div className="pred-podium">
        {PREDICTIONS.map((p, i) => (
          <React.Fragment key={p.pos}>
            <div className="pred-card g-card" style={{ 
              height: p.height, 
              borderTop: `2px solid ${p.accent}`,
              boxShadow: p.pos === 'P1' ? `0 0 40px ${p.accent}20` : 'none'
            }}>
              <div className="pc-pos" style={{ color: p.accent }}>{p.pos}</div>
              
              <div className="pc-driver">
                <div className="pc-code">{p.code}</div>
                <div className="pc-name">{p.name}</div>
                <div className="pc-team">
                  <span className={`team-dot ${p.bgClass}`}></span>
                  {p.team}
                </div>
              </div>

              <div className="pc-prob">
                <div className="prob-bar-bg">
                  <div className="prob-bar-fg" style={{ width: `${p.prob}%` }}></div>
                </div>
                <div className="prob-val">{p.prob}%</div>
              </div>

              <div className="pc-footer">POST-QUALIFYING</div>
            </div>

            {i < 2 && <div className="pred-separator" />}
          </React.Fragment>
        ))}
      </div>

      <div className="pred-model-note">
        Model: XGBoost Ensemble · 96.9% AUC
      </div>

      <style jsx>{`
        .pred-section {
          width: 100%;
          margin-top: 40px;
        }
        .pred-topbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-bottom: 20px;
          border-bottom: 1px solid rgba(225,6,0,0.3);
          margin-bottom: 40px;
        }
        .pt-left {
          font-family: var(--font-mono);
          font-size: 10px;
          color: rgba(255,255,255,0.4);
          letter-spacing: 0.1em;
        }
        .pt-center {
          font-family: var(--font-display);
          font-size: 24px;
          color: var(--white);
          letter-spacing: 0.05em;
        }
        .pt-right {
          font-family: var(--font-mono);
          font-size: 10px;
          color: rgba(255,255,255,0.4);
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .conn-dot {
          width: 6px;
          height: 6px;
          background: #00ff00;
          border-radius: 50%;
          box-shadow: 0 0 8px #00ff00;
          animation: pulseGreen 2s infinite;
        }
        @keyframes pulseGreen {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        
        .pred-podium {
          display: flex;
          align-items: flex-end;
          justify-content: center;
          height: 400px;
          gap: 20px;
          margin-bottom: 30px;
        }
        .pred-card {
          flex: 1;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          padding: 24px;
          background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
        }
        .pred-separator {
          width: 1px;
          height: 80%;
          background: linear-gradient(180deg, transparent, var(--red-dim), transparent);
        }
        .pc-pos {
          font-family: var(--font-display);
          font-size: 48px;
          line-height: 1;
        }
        .pc-code {
          font-family: var(--font-display);
          font-size: clamp(60px, 8vw, 96px);
          line-height: 0.85;
          color: var(--white);
          margin: 16px 0 4px;
        }
        .pc-name {
          font-family: var(--font-body);
          font-size: 12px;
          color: rgba(255,255,255,0.4);
          text-transform: uppercase;
          letter-spacing: 0.1em;
          margin-bottom: 8px;
        }
        .pc-team {
          display: flex;
          align-items: center;
          gap: 8px;
          font-family: var(--font-mono);
          font-size: 10px;
          color: var(--white);
          letter-spacing: 0.1em;
        }
        .team-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }
        .pc-prob {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 24px 0;
        }
        .prob-bar-bg {
          flex: 1;
          height: 4px;
          background: rgba(255,255,255,0.1);
        }
        .prob-bar-fg {
          height: 100%;
          background: var(--red);
          box-shadow: 0 0 10px var(--red);
        }
        .prob-val {
          font-family: var(--font-mono);
          font-size: 14px;
          color: var(--white);
          font-weight: bold;
        }
        .pc-footer {
          font-family: var(--font-mono);
          font-size: 9px;
          color: rgba(255,255,255,0.3);
          letter-spacing: 0.1em;
        }
        .pred-model-note {
          text-align: center;
          font-family: var(--font-mono);
          font-size: 10px;
          color: rgba(255,255,255,0.3);
          letter-spacing: 0.1em;
        }

        @media (max-width: 900px) {
          .pred-podium {
            flex-direction: column;
            height: auto;
            align-items: stretch;
          }
          .pred-card { height: auto !important; }
          .pred-separator { display: none; }
        }
      `}</style>
    </section>
  );
}
