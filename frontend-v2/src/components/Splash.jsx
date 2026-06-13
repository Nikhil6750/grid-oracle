import React, { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';

export default function Splash({ onComplete }) {
  const containerRef = useRef(null);
  const textRef = useRef(null);
  const [shouldPlay, setShouldPlay] = useState(false);

  useEffect(() => {
    const hasPlayed = sessionStorage.getItem('pitwall_splash_played');
    if (hasPlayed) {
      onComplete();
    } else {
      setShouldPlay(true);
      sessionStorage.setItem('pitwall_splash_played', 'true');
    }
  }, [onComplete]);

  useEffect(() => {
    if (!shouldPlay) return;
    
    const chars = textRef.current.querySelectorAll('.splash-char');
    const tl = gsap.timeline({
      onComplete: () => {
        gsap.to(containerRef.current, {
          opacity: 0,
          scale: 1.1,
          duration: 0.6,
          ease: 'power3.inOut',
          onComplete
        });
      }
    });

    tl.to(chars, {
      opacity: 1,
      y: 0,
      scale: 1,
      filter: 'blur(0px)',
      duration: 0.8,
      stagger: 0.05,
      ease: 'power4.out'
    })
    .to(chars, {
      opacity: 0,
      filter: 'blur(10px)',
      scale: 1.2,
      duration: 0.4,
      stagger: 0.02,
      ease: 'power2.in',
      delay: 0.8
    });
    
  }, [shouldPlay, onComplete]);

  if (!shouldPlay) return null;

  const text = "GRID ORACLE";

  return (
    <div className="splash-screen" ref={containerRef}>
      <div className="splash-pill">
        <div className="splash-text" ref={textRef}>
          {text.split('').map((char, i) => (
            <span key={i} className="splash-char">
              {char === ' ' ? '\u00A0' : char}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
