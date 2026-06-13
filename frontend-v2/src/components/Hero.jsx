import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

export default function Hero({ splashDone }) {
  const heroRef = useRef(null);
  const bgRef = useRef(null);
  const rightVizRef = useRef(null);

  useEffect(() => {
    if (!splashDone) return;

    const ctx = gsap.context(() => {
      // Background text parallax (downward)
      ScrollTrigger.create({
        trigger: '.hero-section',
        start: 'top top',
        end: 'bottom top',
        scrub: 1,
        onUpdate: (self) => {
          gsap.set('.hero-content-left', {
            y: self.progress * -80,
            opacity: 1 - self.progress * 1.5
          });
          gsap.set(rightVizRef.current, {
            y: self.progress * -40,
            opacity: 1 - self.progress * 1.2
          });
          gsap.set(bgRef.current, {
            y: self.progress * 150 // scrolls DOWN with parallax
          });
        }
      });

      // Entrance animation
      const tl = gsap.timeline({ delay: 0.2 });
      tl.from('.section-eyebrow', { opacity: 0, x: -20, duration: 0.6, ease: 'power3.out' })
        .from('.hero-tag', { opacity: 0, y: 20, duration: 0.6, ease: 'power3.out' }, '-=0.4')
        .from('.hero-title', { opacity: 0, y: 40, duration: 0.8, ease: 'power3.out' }, '-=0.4')
        .from('.hero-rule', { scaleX: 0, transformOrigin: 'left', duration: 0.8, ease: 'power3.out' }, '-=0.4')
        .from('.hero-sub', { opacity: 0, y: 20, duration: 0.6 }, '-=0.4')
        .from('.hero-pill-btn', { opacity: 0, y: 20, duration: 0.6 }, '-=0.4')
        .from('.hero-scroll-cue', { opacity: 0, duration: 0.6 }, '-=0.2')
        .from(rightVizRef.current, { opacity: 0, x: 50, duration: 1 }, '-=1');

      // Right viz animation loop
      gsap.to('.data-line', {
        scaleX: 'random(0.4, 1)',
        duration: 'random(1, 3)',
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        stagger: 0.2
      });

    }, heroRef);

    return () => ctx.revert();
  }, [splashDone]);

  return (
    <section className="hero-section" ref={heroRef}>
      <div className="hero-bg-glow" />
      <div className="hero-bg-text" ref={bgRef}>GRID ORACLE</div>
      
      <div className="hero-speed-lines">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="speed-line" style={{ top: `${10 + i * 11}%`, animationDelay: `${i * 0.35}s`, opacity: Math.random() * 0.25 + 0.15 }}/>
        ))}
      </div>

      <div className="hero-layout">
        {/* Left 60% */}
        <div className="hero-content-left">
          <div className="section-eyebrow">§ 01 · RACE INTELLIGENCE</div>
          <span className="hero-tag">NIKHIL'S</span>
          <h1 className="hero-title">PIT WALL<span className="hero-dot">.</span></h1>
          <div className="hero-rule" />
          <div className="hero-sub">ML · RACE INTELLIGENCE · 26 <br/> POWERED BY PITWALL AI</div>
          
          <div className="hero-pill-btn">BARCELONA GP ↓</div>
          
          <div className="hero-scroll-cue">
            SCROLL TO IGNITE <div className="hero-scroll-line" />
          </div>
        </div>

        {/* Right 40% */}
        <div className="hero-content-right" ref={rightVizRef}>
          <div className="giant-number">07</div>
          <svg width="100%" height="300" viewBox="0 0 400 300" className="viz-svg">
            {[20, 60, 120, 170, 230, 280].map((y, i) => (
              <g key={i}>
                <circle cx="10" cy={y} r="3" fill="#e10600" opacity="0.8" />
                <rect className="data-line" x="20" y={y - 1} height="2" width="300" fill="#e10600" opacity="0.4" transform-origin="left" />
                <rect x="20" y={y - 1} height="2" width="400" fill="rgba(255,255,255,0.05)" />
              </g>
            ))}
          </svg>
        </div>
      </div>

      <style jsx>{`
        .hero-section {
          position: relative;
          height: 100vh;
          width: 100%;
          overflow: hidden;
          display: flex;
          align-items: center;
          background: transparent;
        }
        .hero-bg-glow {
          position: absolute;
          bottom: 0;
          left: 0;
          width: 60vh;
          height: 60vh;
          background: radial-gradient(circle at bottom left, rgba(225,6,0,0.06) 0%, transparent 70%);
          pointer-events: none;
        }
        .hero-bg-text {
          position: absolute;
          font-family: var(--font-display);
          font-size: clamp(120px, 18vw, 220px);
          color: rgba(225,6,0,0.30);
          writing-mode: vertical-rl;
          text-orientation: mixed;
          transform: translateY(-50%) rotate(180deg);
          right: 80px;
          top: 30%;
          line-height: 1;
          white-space: nowrap;
          letter-spacing: 0.1em;
          pointer-events: none;
          user-select: none;
          z-index: 0;
        }
        .hero-speed-lines {
          position: absolute;
          inset: 0;
          z-index: 1;
          pointer-events: none;
        }
        .speed-line {
          position: absolute;
          width: 60%;
          height: 1px;
          left: -60%;
          background: linear-gradient(90deg, transparent, rgba(225,6,0,1), transparent);
          animation: speedLine 2.8s linear infinite;
        }
        @keyframes speedLine {
          0% { left: -60%; opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { left: 110%; opacity: 0; }
        }
        .hero-layout {
          display: flex;
          width: 100%;
          max-width: 1600px;
          margin: 0 auto;
          padding: 0 var(--section-pad);
          position: relative;
          z-index: 10;
        }
        .hero-content-left {
          flex: 0 0 60%;
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          justify-content: center;
        }
        .hero-tag {
          font-family: var(--font-mono);
          font-size: 14px;
          letter-spacing: 0.35em;
          color: var(--red);
          margin-bottom: 8px;
        }
        .hero-title {
          font-family: var(--font-display);
          font-size: clamp(80px, 12vw, 200px);
          color: var(--white);
          line-height: 0.85;
          margin: 0 0 24px;
        }
        .hero-dot {
          color: var(--red);
        }
        .hero-rule {
          width: 80px;
          height: 2px;
          background: linear-gradient(90deg, var(--red), transparent);
          margin: 16px 0 32px;
          box-shadow: 0 0 12px rgba(225,6,0,0.6);
        }
        .hero-sub {
          font-family: var(--font-mono);
          font-size: 11px;
          letter-spacing: 0.2em;
          color: rgba(255,255,255,0.4);
          text-transform: uppercase;
          margin-bottom: 40px;
          line-height: 1.6;
        }
        .hero-pill-btn {
          display: inline-flex;
          align-items: center;
          padding: 10px 24px;
          background: rgba(225,6,0,0.1);
          border: 1px solid rgba(225,6,0,0.3);
          border-radius: 50px;
          color: var(--red);
          font-family: var(--font-mono);
          font-size: 11px;
          letter-spacing: 0.1em;
          cursor: pointer;
          transition: all 0.3s;
          margin-bottom: 80px;
        }
        .hero-pill-btn:hover {
          background: rgba(225,6,0,0.2);
          border-color: rgba(225,6,0,0.6);
          box-shadow: 0 0 20px rgba(225,6,0,0.2);
        }
        .hero-scroll-cue {
          display: flex;
          align-items: center;
          gap: 16px;
          font-family: var(--font-mono);
          font-size: 9px;
          letter-spacing: 0.3em;
          color: rgba(255,255,255,0.25);
          text-transform: uppercase;
        }
        .hero-scroll-line {
          width: 60px;
          height: 1px;
          background: linear-gradient(90deg, var(--red), transparent);
          animation: cuePulse 2s ease-in-out infinite;
        }
        @keyframes cuePulse {
          0%, 100% { opacity: 0.3; width: 40px; }
          50% { opacity: 1; width: 80px; }
        }
        .hero-content-right {
          flex: 0 0 40%;
          position: relative;
          display: flex;
          align-items: center;
          justify-content: flex-end;
        }
        .giant-number {
          position: absolute;
          font-family: var(--font-display);
          font-size: 300px;
          line-height: 0.8;
          color: rgba(255,255,255,0.04);
          right: 0;
          top: 50%;
          transform: translateY(-50%);
          user-select: none;
        }
        .viz-svg {
          position: relative;
          z-index: 2;
        }
        
        @media (max-width: 900px) {
          .hero-layout { flex-direction: column; justify-content: center; }
          .hero-content-left { flex: 0 0 auto; margin-top: 100px; }
          .hero-content-right { display: none; }
          .hero-bg-text { display: none; }
        }
      `}</style>
    </section>
  );
}
