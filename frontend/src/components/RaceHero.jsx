import React, { useState, useEffect } from 'react';

function RaceHero() {
  const [cd, setCd] = useState({ d: '00', h: '00', m: '00', s: '00' });

  useEffect(() => {
    const target = new Date('2026-05-25T08:00:00Z').getTime();
    const pad = (n) => String(n).padStart(2, '0');

    const tick = () => {
      const diff = target - Date.now();
      if (diff <= 0) {
        setCd({ d: '00', h: '00', m: '00', s: '00' });
        return;
      }
      setCd({
        d: pad(Math.floor(diff / 86400000)),
        h: pad(Math.floor((diff % 86400000) / 3600000)),
        m: pad(Math.floor((diff % 3600000) / 60000)),
        s: pad(Math.floor((diff % 60000) / 1000))
      });
    };

    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <section className="race-hero">
      <div className="race-block">
        <div className="race-grid">
          <div className="race-left">
            <div className="race-meta-row">
              <span className="race-round">◆ Round 05 · Up Next</span>
              <span className="race-flag-big">🇨🇦</span>
            </div>
            <h2 className="race-name">Canadian <em>Grand Prix</em></h2>
            <div className="race-circuit"><strong>Circuit Gilles Villeneuve</strong> · Montreal</div>
            <div className="race-circuit">Round 5 of 23 · 70 laps · 305.270 km</div>

            <div className="race-stats">
              <div className="race-stat">
                <div className="race-stat-label">Lap Record</div>
                <div className="race-stat-val">1:13.078</div>
              </div>
              <div className="race-stat">
                <div className="race-stat-label">Pole Sitter</div>
                <div className="race-stat-val">G. Russell</div>
              </div>
              <div className="race-stat">
                <div className="race-stat-label">Dates</div>
                <div className="race-stat-val">May 25, 2026</div>
              </div>
            </div>
          </div>

          <div className="race-right">
            <div className="countdown-label">Lights Out In</div>
            <div className="countdown">
              <div className="cd-cell"><div className="cd-num">{cd.d}</div><div className="cd-label">Days</div></div>
              <div className="cd-cell"><div className="cd-num">{cd.h}</div><div className="cd-label">Hours</div></div>
              <div className="cd-cell"><div className="cd-num">{cd.m}</div><div className="cd-label">Mins</div></div>
              <div className="cd-cell"><div className="cd-num">{cd.s}</div><div className="cd-label">Secs</div></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default RaceHero;
