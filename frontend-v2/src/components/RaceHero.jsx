import React, { useEffect, useState, useRef } from 'react';
import { gsap } from 'gsap';

// TODO: replace with live API
const MOCK = {
  name: "Barcelona Grand Prix",
  circuit: "Circuit de Barcelona-Catalunya",
  round: "ROUND 07 OF 22",
  laps: "66 LAPS",
  distance: "307 KM",
  time: "15:00 LOCAL",
  date: "Jun 12–14",
  targetDate: "2026-06-14T13:00:00Z"
};

export default function RaceHero() {
  const [timeLeft, setTimeLeft] = useState({ d: 0, h: 0, m: 0, s: 0 });
  const containerRef = useRef(null);

  useEffect(() => {
    const target = new Date(MOCK.targetDate).getTime();
    
    const updateCountdown = () => {
      const now = new Date().getTime();
      const diff = target - now;
      if (diff > 0) {
        setTimeLeft({
          d: Math.floor(diff / (1000 * 60 * 60 * 24)),
          h: Math.floor((diff / (1000 * 60 * 60)) % 24),
          m: Math.floor((diff / 1000 / 60) % 60),
          s: Math.floor((diff / 1000) % 60)
        });
      }
    };
    
    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="race-hero reveal" ref={containerRef}>
      
      {/* Background Decoratives */}
      <div className="race-bg-circuit">
        <svg viewBox="0 0 400 300" preserveAspectRatio="xMidYMid meet">
          <polyline points="50,150 100,100 200,100 250,80 300,120 350,150 320,200 250,220 180,180 120,200 80,180 50,150" 
                    fill="none" stroke="rgba(225,6,0,0.08)" strokeWidth="4" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="race-bg-checker">
        {[...Array(16)].map((_, i) => (
          <div key={i} className="checker-cell" style={{ background: (i + Math.floor(i/4)) % 2 === 0 ? 'rgba(255,255,255,0.03)' : 'transparent' }} />
        ))}
      </div>

      <div className="race-hero-content">
        {/* Left Column */}
        <div className="race-hero-left">
          <div className="rh-badge">{MOCK.round}</div>
          <h2 className="rh-title">{MOCK.name}</h2>
          <div className="rh-meta">
            <span className="rh-circuit">{MOCK.circuit}</span>
            <span className="rh-date">{MOCK.date}</span>
          </div>
          <div className="rh-separator" />
          <div className="rh-pills">
            <div className="rh-pill g-card">{MOCK.laps}</div>
            <div className="rh-pill g-card">{MOCK.distance}</div>
            <div className="rh-pill g-card">{MOCK.time}</div>
          </div>
        </div>

        {/* Right Column */}
        <div className="race-hero-right">
          <div className="countdown-header">
            <div className="countdown-pulse"></div>
            LIGHTS OUT IN
          </div>
          <div className="countdown-timer">
            <div className="cd-cell g-card">
              <div className="cd-value">{String(timeLeft.d).padStart(2, '0')}</div>
              <div className="cd-label">DAYS</div>
            </div>
            <div className="cd-sep">:</div>
            <div className="cd-cell g-card">
              <div className="cd-value">{String(timeLeft.h).padStart(2, '0')}</div>
              <div className="cd-label">HRS</div>
            </div>
            <div className="cd-sep">:</div>
            <div className="cd-cell g-card">
              <div className="cd-value">{String(timeLeft.m).padStart(2, '0')}</div>
              <div className="cd-label">MIN</div>
            </div>
            <div className="cd-sep">:</div>
            <div className="cd-cell g-card">
              <div className="cd-value">{String(timeLeft.s).padStart(2, '0')}</div>
              <div className="cd-label">SEC</div>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .race-hero {
          position: relative;
          padding: var(--card-pad);
          background: rgba(255,255,255,0.01);
          border: 1px solid rgba(255,255,255,0.04);
          border-radius: var(--radius);
          overflow: hidden;
        }
        .race-bg-circuit {
          position: absolute;
          top: -20%;
          right: -10%;
          width: 800px;
          height: 600px;
          pointer-events: none;
          z-index: 0;
        }
        .race-bg-circuit svg {
          width: 100%;
          height: 100%;
        }
        .race-bg-checker {
          position: absolute;
          top: 0;
          right: 0;
          width: 48px;
          height: 48px;
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          grid-template-rows: repeat(4, 1fr);
          opacity: 0.5;
        }
        .race-hero-content {
          position: relative;
          z-index: 10;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 40px;
          align-items: center;
        }
        .rh-badge {
          display: inline-block;
          padding: 6px 12px;
          background: var(--red);
          color: var(--white);
          font-family: var(--font-mono);
          font-size: 10px;
          letter-spacing: 0.1em;
          border-radius: 50px;
          margin-bottom: 24px;
        }
        .rh-title {
          font-family: var(--font-display);
          font-size: clamp(48px, 6vw, 72px);
          line-height: 0.9;
          color: var(--white);
          margin: 0 0 16px;
        }
        .rh-meta {
          display: flex;
          flex-direction: column;
          gap: 6px;
          margin-bottom: 32px;
        }
        .rh-circuit {
          font-family: var(--font-mono);
          font-size: 13px;
          color: rgba(255,255,255,0.4);
        }
        .rh-date {
          font-family: var(--font-body);
          font-size: 13px;
          color: var(--white);
        }
        .rh-separator {
          width: 100%;
          height: 1px;
          background: linear-gradient(90deg, var(--red-dim), transparent);
          margin-bottom: 32px;
        }
        .rh-pills {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }
        .rh-pill {
          padding: 8px 16px;
          font-family: var(--font-mono);
          font-size: 11px;
          letter-spacing: 0.1em;
          color: var(--white);
        }
        .countdown-header {
          display: flex;
          align-items: center;
          gap: 12px;
          font-family: var(--font-mono);
          font-size: 10px;
          color: var(--red);
          letter-spacing: 0.15em;
          margin-bottom: 20px;
        }
        .countdown-pulse {
          width: 6px;
          height: 6px;
          background: var(--red);
          border-radius: 50%;
          box-shadow: 0 0 8px var(--red);
          animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.8); }
        }
        .countdown-timer {
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .cd-cell {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          width: 80px;
          height: 90px;
          border-radius: var(--radius-sm);
        }
        .cd-value {
          font-family: var(--font-display);
          font-size: clamp(48px, 6vw, 88px);
          line-height: 0.8;
          color: var(--white);
          margin-top: 8px;
        }
        .cd-label {
          font-family: var(--font-mono);
          font-size: 9px;
          color: rgba(255,255,255,0.4);
          margin-top: 8px;
        }
        .cd-sep {
          font-family: var(--font-display);
          font-size: 40px;
          color: var(--red);
          transform: translateY(-8px);
        }
        
        @media (max-width: 900px) {
          .race-hero-content { grid-template-columns: 1fr; }
          .countdown-timer { flex-wrap: wrap; }
          .race-bg-circuit { opacity: 0.2; }
        }
      `}</style>
    </section>
  );
}
