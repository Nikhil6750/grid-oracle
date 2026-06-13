import React from 'react';

export default function Footer() {
  return (
    <footer className="footer-section">
      <div className="red-rule full-width-rule" />
      
      <div className="footer-content">
        
        {/* Left Column */}
        <div className="fc-left">
          <div className="fc-title">PITWALL AI</div>
          <div className="fc-sub">Race Intelligence · 2026</div>
          <a href="#" className="github-btn g-card">
            GITHUB REPOSITORY ↗
          </a>
        </div>
        
        {/* Right Column */}
        <div className="fc-right">
          <div className="tech-stack">
            {['FastAPI', 'XGBoost', 'OpenF1', 'React', 'GSAP'].map(tech => (
              <span key={tech} className="tech-pill g-card">{tech}</span>
            ))}
          </div>
          <div className="fc-credit">Built by Nikhil</div>
          <div className="fc-inspire">Inspired by Mariana Antaya's F1 ML work</div>
        </div>

      </div>

      {/* Bottom Bar */}
      <div className="footer-bottom">
        <div className="fb-left">FOR NIKHIL · EYES ONLY · LIGHTS OUT</div>
        <div className="fb-right">THE PIT WALL</div>
      </div>

      <style jsx>{`
        .footer-section {
          width: 100%;
          margin-top: 120px;
          padding-bottom: 40px;
        }
        .full-width-rule {
          margin-bottom: 60px;
        }
        .footer-content {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 80px;
        }
        .fc-left {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 12px;
        }
        .fc-title {
          font-family: var(--font-display);
          font-size: 48px;
          color: var(--white);
          line-height: 1;
        }
        .fc-sub {
          font-family: var(--font-mono);
          font-size: 11px;
          color: rgba(255,255,255,0.4);
          letter-spacing: 0.15em;
          margin-bottom: 12px;
        }
        .github-btn {
          font-family: var(--font-mono);
          font-size: 10px;
          letter-spacing: 0.1em;
          color: var(--white);
          padding: 10px 16px;
        }
        .github-btn:hover {
          color: var(--red);
        }
        
        .fc-right {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 16px;
          text-align: right;
        }
        .tech-stack {
          display: flex;
          flex-wrap: wrap;
          justify-content: flex-end;
          gap: 8px;
          max-width: 400px;
          margin-bottom: 8px;
        }
        .tech-pill {
          font-family: var(--font-mono);
          font-size: 10px;
          color: rgba(255,255,255,0.6);
          padding: 6px 12px;
          border-radius: 50px;
        }
        .fc-credit {
          font-family: var(--font-body);
          font-size: 13px;
          color: rgba(255,255,255,0.4);
        }
        .fc-inspire {
          font-family: var(--font-body);
          font-size: 11px;
          font-style: italic;
          color: rgba(255,255,255,0.4);
        }

        .footer-bottom {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 24px;
          border-top: 1px solid rgba(255,255,255,0.05);
        }
        .fb-left {
          font-family: var(--font-mono);
          font-size: 9px;
          color: rgba(255,255,255,0.3);
          letter-spacing: 0.2em;
        }
        .fb-right {
          font-family: 'Georgia', serif;
          font-style: italic;
          font-size: 12px;
          color: rgba(255,255,255,0.3);
          letter-spacing: 0.1em;
        }

        @media (max-width: 768px) {
          .footer-content {
            flex-direction: column;
            gap: 40px;
            align-items: flex-start;
          }
          .fc-right {
            align-items: flex-start;
            text-align: left;
          }
          .tech-stack { justify-content: flex-start; }
          .footer-bottom {
            flex-direction: column;
            gap: 16px;
            align-items: flex-start;
          }
        }
      `}</style>
    </footer>
  );
}
