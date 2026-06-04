import React from 'react';

function StatsRibbon() {
  return (
    <section className="stats-ribbon">
      <div className="stats-grid">
        <div className="stat">
          <div className="stat-label">Championship Lead</div>
          <div className="stat-big"><em>+43</em> pts</div>
          <div className="stat-sub">Antonelli over Russell</div>
        </div>
        <div className="stat">
          <div className="stat-label">Last Race Winner</div>
          <div className="stat-big">K. Antonelli</div>
          <div className="stat-sub">Canadian GP · Montreal</div>
        </div>
        <div className="stat">
          <div className="stat-label">Next Race</div>
          <div className="stat-big">Monaco GP<em></em></div>
          <div className="stat-sub">Jun 07 · Monte Carlo</div>
        </div>
        <div className="stat">
          <div className="stat-label">Verstappen Gap</div>
          <div className="stat-big">P7 <em>·</em> −88</div>
          <div className="stat-sub">After 5 rounds</div>
        </div>
      </div>
    </section>
  );
}

export default StatsRibbon;
