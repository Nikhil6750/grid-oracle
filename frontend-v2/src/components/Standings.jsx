import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

// TODO: replace with live API
const MOCK = [
  { pos: 1, driver: 'ANT', points: 156, team: 'Mercedes', teamId: 'mercedes', color: 'var(--team-mercedes)' },
  { pos: 2, driver: 'HAM', points: 90, team: 'Ferrari', teamId: 'ferrari', color: 'var(--team-ferrari)' },
  { pos: 3, driver: 'RUS', points: 88, team: 'Mercedes', teamId: 'mercedes', color: 'var(--team-mercedes)' },
  { pos: 4, driver: 'LEC', points: 75, team: 'Ferrari', teamId: 'ferrari', color: 'var(--team-ferrari)' },
  { pos: 5, driver: 'PIA', points: 60, team: 'McLaren', teamId: 'mclaren', color: 'var(--team-mclaren)' },
  { pos: 6, driver: 'NOR', points: 58, team: 'McLaren', teamId: 'mclaren', color: 'var(--team-mclaren)' },
  { pos: 7, driver: 'VER', points: 43, team: 'Red Bull', teamId: 'redbull', color: 'var(--team-redbull)' },
  { pos: 8, driver: 'HAD', points: 40, team: 'Red Bull', teamId: 'redbull', color: 'var(--team-redbull)' },
  { pos: 9, driver: 'GAS', points: 20, team: 'Alpine', teamId: 'alpine', color: 'var(--team-alpine)' },
  { pos: 10, driver: 'BEA', points: 18, team: 'Haas', teamId: 'haas', color: 'var(--team-haas)' }
];

export default function Standings() {
  const containerRef = useRef(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Reveal table rows
      gsap.from('.st-row', {
        opacity: 0,
        x: -20,
        duration: 0.5,
        stagger: 0.05,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: containerRef.current,
          start: "top 80%"
        }
      });

      // Animate chart bars
      gsap.fromTo('.chart-bar-fill',
        { scaleX: 0 },
        {
          scaleX: 1,
          duration: 1,
          stagger: 0.08,
          ease: 'power3.out',
          transformOrigin: 'left',
          scrollTrigger: {
            trigger: containerRef.current,
            start: "top 80%"
          }
        }
      );
    }, containerRef);

    return () => ctx.revert();
  }, []);

  const maxPoints = Math.max(...MOCK.map(d => d.points));

  return (
    <section className="standings-section reveal" ref={containerRef}>
      
      <div className="st-left">
        <h3 className="st-title">DRIVERS' CHAMPIONSHIP</h3>
        <div className="st-table">
          {MOCK.map((row) => (
            <div key={row.pos} className="st-row">
              <div 
                className="st-accent" 
                style={{ background: row.pos === 1 ? 'var(--team-gold)' : row.color }} 
              />
              <div className="st-pos">{row.pos}</div>
              <div className="st-driver">{row.driver}</div>
              <div className="st-team">{row.team}</div>
              <div className="st-points">{row.points} PTS</div>
            </div>
          ))}
        </div>
      </div>

      <div className="st-right">
        <div className="giant-points">{MOCK[0].points} PTS</div>
        <div className="st-chart">
          {MOCK.map((row) => {
            const widthPct = (row.points / maxPoints) * 100;
            return (
              <div key={row.pos} className="chart-row">
                <div className="chart-label">{row.driver}</div>
                <div className="chart-bar-bg">
                  <div 
                    className="chart-bar-fill"
                    style={{ 
                      width: `${widthPct}%`, 
                      background: row.color,
                      boxShadow: `0 0 10px ${row.color}40`
                    }} 
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <style jsx>{`
        .standings-section {
          display: flex;
          gap: 60px;
          margin-top: 60px;
        }
        .st-left {
          flex: 0 0 45%;
        }
        .st-right {
          flex: 0 0 55%;
          position: relative;
          display: flex;
          align-items: center;
        }
        
        /* Table */
        .st-title {
          font-family: var(--font-display);
          font-size: clamp(32px, 4vw, 48px);
          color: var(--white);
          margin-bottom: 32px;
          letter-spacing: 0.02em;
        }
        .st-table {
          display: flex;
          flex-direction: column;
        }
        .st-row {
          display: flex;
          align-items: center;
          height: 52px;
          border-bottom: 1px solid rgba(255,255,255,0.05);
          transition: background 0.2s;
        }
        .st-row:hover {
          background: rgba(225,6,0,0.04);
        }
        .st-accent {
          width: 3px;
          height: 100%;
          margin-right: 16px;
        }
        .st-pos {
          width: 32px;
          font-family: var(--font-mono);
          font-size: 14px;
          color: rgba(255,255,255,0.4);
        }
        .st-driver {
          width: 60px;
          font-family: var(--font-display);
          font-size: 22px;
          color: var(--white);
          letter-spacing: 0.05em;
          padding-top: 4px;
        }
        .st-team {
          flex: 1;
          font-family: var(--font-body);
          font-size: 12px;
          color: rgba(255,255,255,0.4);
        }
        .st-points {
          font-family: var(--font-mono);
          font-size: 20px;
          font-weight: bold;
          color: var(--white);
          text-align: right;
        }
        
        /* Chart */
        .giant-points {
          position: absolute;
          font-family: var(--font-display);
          font-size: 200px;
          color: rgba(255,255,255,0.03);
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          white-space: nowrap;
          pointer-events: none;
        }
        .st-chart {
          width: 100%;
          display: flex;
          flex-direction: column;
          gap: 16px;
          position: relative;
          z-index: 2;
        }
        .chart-row {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .chart-label {
          font-family: var(--font-mono);
          font-size: 10px;
          color: rgba(255,255,255,0.6);
          letter-spacing: 0.1em;
        }
        .chart-bar-bg {
          width: 100%;
          height: 8px;
          background: rgba(255,255,255,0.05);
          border-radius: 4px;
          overflow: hidden;
        }
        .chart-bar-fill {
          height: 100%;
          border-radius: 4px;
        }

        @media (max-width: 900px) {
          .standings-section { flex-direction: column; }
          .st-left, .st-right { flex: 1 1 auto; }
          .giant-points { display: none; }
        }
      `}</style>
    </section>
  );
}
