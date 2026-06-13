import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

const STATS = [
  { eyebrow: 'CHAMPIONSHIP LEAD', value: '+43', unit: 'PTS', sub: 'ANT over RUS', isNumber: true, target: 43 },
  { eyebrow: 'LAST RACE WINNER', value: 'A. ANT', unit: '', sub: 'Monaco GP', isNumber: false },
  { eyebrow: 'NEXT RACE', value: 'BCN', unit: 'GP', sub: 'Jun 14, 2026', isNumber: false },
  { eyebrow: 'ROUNDS COMPLETE', value: '6', unit: '/ 22', sub: '2026 Season', isNumber: true, target: 6 },
];

export default function StatsRibbon() {
  const ribbonRef = useRef(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const numberEls = document.querySelectorAll('.stat-count');
      
      numberEls.forEach(el => {
        const target = parseFloat(el.getAttribute('data-target'));
        if (isNaN(target)) return;
        
        ScrollTrigger.create({
          trigger: ribbonRef.current,
          start: 'top 80%',
          onEnter: () => {
            gsap.fromTo(el, 
              { innerHTML: 0 },
              {
                innerHTML: target,
                duration: 2,
                ease: 'power3.out',
                snap: { innerHTML: 1 },
                onUpdate: function() {
                  // Re-append any prefix/suffix if needed, but our setup splits them
                  el.innerHTML = Math.round(this.targets()[0].innerHTML);
                }
              }
            );
          },
          once: true
        });
      });
      
      // Reveal items
      gsap.from('.ribbon-stat-card', {
        y: 30,
        opacity: 0,
        duration: 0.8,
        stagger: 0.1,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: ribbonRef.current,
          start: 'top 80%'
        }
      });
    }, ribbonRef);

    return () => ctx.revert();
  }, []);

  return (
    <section className="stats-ribbon" ref={ribbonRef}>
      <div className="ribbon-container">
        {STATS.map((stat, i) => (
          <React.Fragment key={i}>
            <div className="ribbon-stat-card">
              <div className="rs-eyebrow">{stat.eyebrow}</div>
              <div className="rs-value-group">
                {stat.isNumber && stat.value.startsWith('+') && <span className="rs-prefix">+</span>}
                <span className={`rs-value ${stat.isNumber ? 'stat-count' : ''}`} data-target={stat.target}>
                  {stat.isNumber ? stat.value.replace('+', '') : stat.value}
                </span>
                {stat.unit && <span className="rs-unit">{stat.unit}</span>}
              </div>
              <div className="rs-sub">{stat.sub}</div>
              <div className="rs-hover-line" />
            </div>
            {i < STATS.length - 1 && <div className="rs-separator" />}
          </React.Fragment>
        ))}
      </div>

      <style jsx>{`
        .stats-ribbon {
          width: 100vw;
          margin-left: calc(-50vw + 50%);
          background: rgba(225,6,0,0.04);
          border-top: 1px solid rgba(225,6,0,0.15);
          border-bottom: 1px solid rgba(225,6,0,0.15);
          padding: 60px 0;
          margin-top: 80px;
          margin-bottom: 80px;
        }
        .ribbon-container {
          max-width: 1600px;
          margin: 0 auto;
          padding: 0 var(--section-pad);
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .ribbon-stat-card {
          flex: 1;
          display: flex;
          flex-direction: column;
          position: relative;
          padding: 0 20px;
          group: hover; /* placeholder for potential tailwind logic if used, but we use normal hover */
        }
        .rs-separator {
          width: 1px;
          height: 80px;
          background: rgba(255,255,255,0.06);
        }
        .rs-eyebrow {
          font-family: var(--font-mono);
          font-size: 9px;
          letter-spacing: 0.25em;
          color: rgba(255,255,255,0.4);
          text-transform: uppercase;
          margin-bottom: 16px;
        }
        .rs-value-group {
          display: flex;
          align-items: baseline;
          gap: 8px;
        }
        .rs-prefix {
          font-family: var(--font-display);
          font-size: clamp(32px, 5vw, 64px);
          color: var(--white);
        }
        .rs-value {
          font-family: var(--font-display);
          font-size: clamp(48px, 7vw, 96px);
          line-height: 0.9;
          color: var(--white);
        }
        .rs-unit {
          font-family: var(--font-display);
          font-size: clamp(24px, 3vw, 48px);
          color: var(--white);
        }
        .rs-sub {
          font-family: var(--font-body);
          font-size: 13px;
          color: rgba(255,255,255,0.4);
          margin-top: 12px;
        }
        .rs-hover-line {
          position: absolute;
          bottom: -20px;
          left: 20px;
          height: 2px;
          width: 0;
          background: var(--red);
          transition: width 0.4s ease;
        }
        .ribbon-stat-card:hover .rs-hover-line {
          width: 60px;
        }
        
        @media (max-width: 900px) {
          .ribbon-container {
            flex-direction: column;
            gap: 40px;
          }
          .rs-separator {
            width: 80%;
            height: 1px;
          }
          .ribbon-stat-card {
            align-items: center;
            text-align: center;
          }
          .rs-hover-line {
            left: 50%;
            transform: translateX(-50%);
          }
        }
      `}</style>
    </section>
  );
}
