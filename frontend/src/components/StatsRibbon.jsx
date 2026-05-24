import React from 'react';

function StatsRibbon() {
  return (
    <section className="stats-ribbon">
      <div className="stats-grid">
        <div className="stat">
          <div className="stat-label">Championship Lead</div>
          <div className="stat-big"><em>+18</em> pts</div>
          <div className="stat-sub">Antonelli over Russell</div>
        </div>
        <div className="stat">
          <div className="stat-label">Pole Position</div>
          <div className="stat-big">G. Russell</div>
          <div className="stat-sub">Canadian GP · 2026</div>
        </div>
        <div className="stat">
          <div className="stat-label">Sprint Winner</div>
          <div className="stat-big">G. Russell<em></em></div>
          <div className="stat-sub">Canadian GP · Montreal</div>
        </div>
        <div className="stat">
          <div className="stat-label">Verstappen Gap</div>
          <div className="stat-big">P6 <em>·</em> −60</div>
          <div className="stat-sub">Qualified 6th in Canada</div>
        </div>
      </div>
    </section>
  );
}

export default StatsRibbon;
