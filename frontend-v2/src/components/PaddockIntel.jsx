import React from 'react';

// TODO: replace with live API
const MOCK = {
  podium: {
    race: "Monaco",
    p1: "ANT",
    p1Color: "var(--team-mercedes)",
    p2: "HAM",
    p2Color: "var(--team-ferrari)",
    p3: "HAD",
    p3Color: "var(--team-redbull)"
  },
  news: [
    { category: "TITLE RACE", title: "Antonelli extends lead to 43 points after Monaco win", body: "The Mercedes rookie continues his incredible 2026 campaign, securing maximum points while rivals falter." },
    { category: "STRATEGY", title: "Hamilton P2 — Ferrari's tyre call vindicated in Monte Carlo", body: "An aggressive overcut strategy allowed Hamilton to jump two places in the tight streets." },
    { category: "RELIABILITY", title: "Verstappen retirement deepens Red Bull's 2026 crisis", body: "Power unit failure on lap 14 marks the third DNF for the defending champion this season." },
    { category: "GRID ORACLE", title: "PitWall AI called 2 of 3 Monaco podium spots — beating ChatGPT and Gemini", body: "Our XGBoost ensemble accurately predicted the podium finishers with 94% confidence." }
  ]
};

export default function PaddockIntel() {
  return (
    <section className="intel-section reveal">
      <div className="section-eyebrow">§ 06 · EDITORIAL</div>
      <h3 className="section-title">PADDOCK INTEL</h3>
      <div className="red-rule" />

      <div className="intel-layout">
        
        {/* Left 35% */}
        <div className="intel-left">
          <div className="intel-eyebrow">LAST RACE · {MOCK.podium.race.toUpperCase()}</div>
          <div className="podium-viz">
            <div className="podium-col p2-col g-card">
              <div className="pd-driver">{MOCK.podium.p2}</div>
              <div className="pd-label">P2</div>
              <div className="pd-fill" style={{ background: MOCK.podium.p2Color }} />
            </div>
            <div className="podium-col p1-col g-card">
              <div className="pd-driver">{MOCK.podium.p1}</div>
              <div className="pd-label">P1</div>
              <div className="pd-fill" style={{ background: MOCK.podium.p1Color }} />
            </div>
            <div className="podium-col p3-col g-card">
              <div className="pd-driver">{MOCK.podium.p3}</div>
              <div className="pd-label">P3</div>
              <div className="pd-fill" style={{ background: MOCK.podium.p3Color }} />
            </div>
          </div>
        </div>

        {/* Right 65% */}
        <div className="intel-right">
          <div className="news-grid">
            {MOCK.news.map((item, i) => (
              <div key={i} className="news-card g-card">
                <div className="nc-badge">{item.category}</div>
                <h4 className="nc-title">{item.title}</h4>
                <p className="nc-body">{item.body}</p>
              </div>
            ))}
          </div>
        </div>

      </div>

      <style jsx>{`
        .intel-section {
          width: 100%;
          margin-top: 100px;
        }
        .intel-layout {
          display: flex;
          gap: 40px;
        }
        .intel-left {
          flex: 0 0 35%;
        }
        .intel-right {
          flex: 0 0 calc(65% - 40px);
        }
        
        /* Podium Viz */
        .intel-eyebrow {
          font-family: var(--font-mono);
          font-size: 11px;
          letter-spacing: 0.2em;
          color: rgba(255,255,255,0.5);
          margin-bottom: 32px;
        }
        .podium-viz {
          display: flex;
          align-items: flex-end;
          gap: 12px;
          height: 240px;
        }
        .podium-col {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: flex-start;
          padding-top: 16px;
          position: relative;
          overflow: hidden;
        }
        .p1-col { height: 160px; }
        .p2-col { height: 120px; }
        .p3-col { height: 100px; }
        
        .pd-driver {
          font-family: var(--font-display);
          font-size: 32px;
          line-height: 1;
          color: var(--white);
          z-index: 2;
        }
        .pd-label {
          font-family: var(--font-mono);
          font-size: 10px;
          color: rgba(255,255,255,0.6);
          margin-top: 4px;
          z-index: 2;
        }
        .pd-fill {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          height: 100%;
          opacity: 0.15;
          z-index: 1;
        }
        .p1-col .pd-fill { opacity: 0.25; }

        /* News Grid */
        .news-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        .news-card {
          padding: 24px;
          display: flex;
          flex-direction: column;
          border-left: 2px solid transparent;
          transition: transform 0.3s, border-left-color 0.3s, background 0.3s;
          cursor: pointer;
        }
        .news-card:hover {
          transform: translateY(-4px);
          border-left-color: var(--red);
          background: rgba(255,255,255,0.05);
        }
        .nc-badge {
          align-self: flex-start;
          background: var(--red);
          color: var(--white);
          font-family: var(--font-mono);
          font-size: 8px;
          padding: 4px 8px;
          letter-spacing: 0.15em;
          margin-bottom: 16px;
        }
        .nc-title {
          font-family: var(--font-condensed);
          font-size: 20px;
          line-height: 1.3;
          color: var(--white);
          margin-bottom: 12px;
        }
        .nc-body {
          font-family: var(--font-body);
          font-size: 13px;
          color: rgba(255,255,255,0.4);
          line-height: 1.5;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        @media (max-width: 900px) {
          .intel-layout { flex-direction: column; }
          .news-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </section>
  );
}
