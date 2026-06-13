import React, { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';

export default function SpeedCursor() {
  const arcRef = useRef(null);
  const needleRef = useRef(null);
  const maxRef = useRef(null);
  const containerRef = useRef(null);
  const [speed, setSpeed] = useState(0);
  const [isTouch, setIsTouch] = useState(false);

  useEffect(() => {
    if (window.matchMedia('(max-width: 768px)').matches || window.matchMedia('(hover: none) and (pointer: coarse)').matches) {
      setIsTouch(true);
      return;
    }

    let lastX = 0;
    let lastY = 0;
    let lastTime = performance.now();
    let displaySpeed = 0;
    
    let localMax = parseInt(sessionStorage.getItem('pw_max_speed') || '0', 10);
    if (maxRef.current) maxRef.current.innerText = `MAX ${localMax}`;
    
    let instantaneousKmh = 0;

    const handleMouseMove = (e) => {
      const currentTime = performance.now();
      if (lastX === 0 && lastY === 0) {
        lastX = e.clientX;
        lastY = e.clientY;
        lastTime = currentTime;
        return;
      }
      
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const dt = currentTime - lastTime;
      
      if (dt > 0) {
        const pxPerSec = (dist / dt) * 1000;
        instantaneousKmh = pxPerSec / 8;
        if (instantaneousKmh > 300) instantaneousKmh = 300;
      }

      lastX = e.clientX;
      lastY = e.clientY;
      lastTime = currentTime;
    };

    window.addEventListener('mousemove', handleMouseMove);

    const renderLoop = () => {
      displaySpeed = displaySpeed * 0.85 + instantaneousKmh * 0.15;
      instantaneousKmh *= 0.9;
      
      if (displaySpeed < 1) displaySpeed = 0;
      if (displaySpeed > 300) displaySpeed = 300;
      
      const intSpeed = Math.round(displaySpeed);
      setSpeed(intSpeed);
      
      if (intSpeed > localMax) {
        localMax = intSpeed;
        if (maxRef.current) maxRef.current.innerText = `MAX ${localMax}`;
        sessionStorage.setItem('pw_max_speed', localMax.toString());
      }

      // Determine color
      let color = 'rgba(255,255,255,0.3)';
      if (displaySpeed > 100 && displaySpeed <= 200) color = 'rgba(255,165,0,0.6)';
      if (displaySpeed > 200) color = 'rgba(225,6,0,0.9)';
      
      if (containerRef.current) {
        if (displaySpeed > 150) {
          containerRef.current.style.boxShadow = '0 0 30px rgba(225,6,0,0.4)';
          containerRef.current.style.borderColor = 'rgba(225,6,0,0.3)';
        } else {
          containerRef.current.style.boxShadow = '0 4px 24px rgba(0,0,0,0.4)';
          containerRef.current.style.borderColor = 'rgba(255,255,255,0.06)';
        }
      }
      
      if (needleRef.current) {
        needleRef.current.style.stroke = color;
        gsap.to(needleRef.current, {
          rotation: -120 + (displaySpeed / 300) * 240,
          duration: 0.4,
          ease: 'elastic.out(1, 0.45)',
          transformOrigin: '80px 80px',
          overwrite: true
        });
      }
      
      if (arcRef.current) {
        arcRef.current.style.stroke = color;
        const offset = 100 - (displaySpeed / 300) * 100;
        gsap.to(arcRef.current, {
          strokeDashoffset: offset,
          duration: 0.3,
          overwrite: true
        });
        arcRef.current.style.opacity = 0.5 + (displaySpeed / 300) * 0.5;
      }
      
      requestAnimationFrame(renderLoop);
    };

    const animId = requestAnimationFrame(renderLoop);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animId);
    };
  }, []);

  if (isTouch) return null;

  const polarToCartesian = (cx, cy, r, angleInDegrees) => {
    const angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
    return {
      x: cx + (r * Math.cos(angleInRadians)),
      y: cy + (r * Math.sin(angleInRadians))
    };
  };

  const describeArc = (x, y, r, startAngle, endAngle) => {
    const start = polarToCartesian(x, y, r, endAngle);
    const end = polarToCartesian(x, y, r, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
    return [
      "M", start.x, start.y, 
      "A", r, r, 0, largeArcFlag, 0, end.x, end.y
    ].join(" ");
  };

  const arcPath = describeArc(80, 80, 60, -120, 120);

  const ticks = Array.from({ length: 11 }).map((_, i) => {
    const angle = -120 + i * 24;
    const p1 = polarToCartesian(80, 80, 60, angle);
    const p2 = polarToCartesian(80, 80, 52, angle);
    return <line key={i} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="rgba(255,255,255,0.35)" strokeWidth="2" />;
  });

  const labels = [0, 100, 200, 300].map((val, i) => {
    const angles = [-120, -40, 40, 120];
    const pos = polarToCartesian(80, 80, 42, angles[i]);
    return (
      <text key={val} x={pos.x} y={pos.y + 2.5} fontSize="8px" fontFamily="var(--font-mono)" fill="rgba(255,255,255,0.4)" textAnchor="middle">
        {val}
      </text>
    );
  });

  return (
    <div ref={containerRef} style={{
      position: 'fixed', bottom: '30px', right: '30px', zIndex: 900,
      width: '180px', height: '180px', overflow: 'visible',
      display: 'flex', justifyContent: 'center', alignItems: 'center',
      background: 'var(--glass-bg)', border: '1px solid var(--glass-border)',
      backdropFilter: 'var(--glass-blur)', WebkitBackdropFilter: 'var(--glass-blur)',
      borderRadius: '50%', padding: '10px',
      transition: 'box-shadow 0.3s, border-color 0.3s'
    }}>
      <style>{`
        @media (max-width: 768px) {
          div[style*="z-index: 900"] {
            display: none !important;
          }
        }
      `}</style>
      <div ref={maxRef} style={{ position: 'absolute', top: '22px', width: '100%', textAlign: 'center', fontSize: '9px', color: '#e10600', fontFamily: 'var(--font-mono)' }}>
        MAX 0
      </div>

      <svg viewBox="0 0 160 160" width="160" height="160" style={{ display: 'block' }}>
        <defs>
          <filter id="glow-cursor"><feGaussianBlur stdDeviation="3"/></filter>
        </defs>

        <path d={arcPath} stroke="rgba(255,255,255,0.12)" strokeWidth="5" fill="none" strokeLinecap="round" />
        
        <path d={arcPath} ref={arcRef} stroke="rgba(255,255,255,0.3)" strokeWidth="5" fill="none" strokeLinecap="round" pathLength="100" strokeDasharray="100" strokeDashoffset="100" filter="url(#glow-cursor)" style={{ opacity: 0.5 }} />

        {ticks}
        {labels}

        <line x1="80" y1="80" x2="80" y2="34" stroke="rgba(255,255,255,0.3)" strokeWidth="3" strokeLinecap="round" ref={needleRef} style={{ transformOrigin: '80px 80px', transform: 'rotate(-120deg)' }} />

        <circle cx="80" cy="80" r="6" fill="var(--white)" />

        <text x="80" y="116" fontSize="22px" fontFamily="var(--font-mono)" fill="#fff" textAnchor="middle" fontWeight="bold">{speed}</text>
        <text x="80" y="128" fontSize="8px" fill="rgba(255,255,255,0.4)" textAnchor="middle" fontFamily="var(--font-mono)">km/h</text>
        <text x="80" y="146" fontSize="7px" fontFamily="var(--font-mono)" letterSpacing="0.15em" fill="rgba(255,255,255,0.3)" textAnchor="middle">PITWALL AI</text>
      </svg>
    </div>
  );
}
