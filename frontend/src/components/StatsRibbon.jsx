import React from 'react';

function StatsRibbon() {
  return (
    <section className="stats-ribbon">
      <div className="stats-grid">
        <div className="stat">
          <div className="stat-label">Championship Lead</div>
          <div className="stat-big"><em>+9</em> pts</div>
          <div className="stat-sub">Antonelli over Russell</div>
        </div>
        <div className="stat">
          <div className="stat-label">Fastest Lap 2026</div>
          <div className="stat-big">1:28.411</div>
          <div className="stat-sub">Russell · Japan Q3</div>
        </div>
        <div className="stat">
          <div className="stat-label">Fastest Pit Stop</div>
          <div className="stat-big">1.94<em>s</em></div>
          <div className="stat-sub">McLaren · Japanese GP</div>
        </div>
        <div className="stat">
          <div className="stat-label">Verstappen Gap</div>
          <div className="stat-big">P9 <em>·</em> −60</div>
          <div className="stat-sub">Worst start since 2017</div>
        </div>
      </div>
    </section>
  );
}

export default StatsRibbon;
