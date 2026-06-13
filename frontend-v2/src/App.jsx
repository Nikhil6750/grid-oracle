import React, { useEffect, useState, useRef } from 'react';
import Lenis from '@studio-freight/lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

import SplashScreen from './components/SplashScreen';
import Ticker from './components/Ticker';
import Hero from './components/Hero';
import RaceHero from './components/RaceHero';
import PredictionPanel from './components/PredictionPanel';
import SessionResults from './components/SessionResults';
import StatsRibbon from './components/StatsRibbon';
import Standings from './components/Standings';
import Calendar from './components/Calendar';
import PaddockIntel from './components/PaddockIntel';
import Footer from './components/Footer';
import SpeedCursor from './components/SpeedCursor';
import NavDots from './components/NavDots';

gsap.registerPlugin(ScrollTrigger);

const SECTION_COUNT = 7;

function App() {
  const [splashDone, setSplashDone] = useState(!!sessionStorage.getItem('splashShown'));
  const appRef = useRef(null);

  useEffect(() => {
    if (!splashDone) return;
    
    const lenis = new Lenis({ smoothWheel: true, lerp: 0.07 });
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);

    const ctx = gsap.context(() => {
      const sections = gsap.utils.toArray('.snap-section');
      
      sections.forEach((section, i) => {
        if (i === 0) return; // Skip Hero since it handles its own entrance
        
        gsap.fromTo(section, 
          { opacity: 0, y: 40, scale: 0.98, filter: 'blur(4px)' },
          {
            opacity: 1, 
            y: 0, 
            scale: 1, 
            filter: 'blur(0px)',
            duration: 0.9, 
            ease: 'power3.out',
            scrollTrigger: {
              trigger: section, 
              start: 'top 80%',
              toggleActions: 'play none none reverse'
            }
          }
        );
      });
    }, appRef);

    return () => {
      lenis.destroy();
      ctx.revert();
    };
  }, [splashDone]);

  return (
    <>
      <SplashScreen onDone={() => setSplashDone(true)} />

      <div className="app-wrapper" ref={appRef}>
        <SpeedCursor />
        <Ticker />

        <section className="snap-section" id="section-0">
          <Hero splashDone={splashDone} />
        </section>

        <section className="snap-section" id="section-1">
          <div className="container" style={{ paddingTop: '100px' }}>
            <RaceHero />
          </div>
        </section>

        <section className="snap-section" id="section-2">
          <div className="container">
            <PredictionPanel />
            <SessionResults />
          </div>
        </section>

        <section className="snap-section" id="section-3">
          <StatsRibbon />
        </section>

        <section className="snap-section" id="section-4">
          <div className="container">
            <Standings />
          </div>
        </section>

        <section className="snap-section" id="section-5">
          <div className="container">
            <Calendar />
          </div>
        </section>

        <section className="snap-section" id="section-6">
          <div className="container">
            <PaddockIntel />
            <Footer />
          </div>
        </section>
      </div>

      <NavDots count={SECTION_COUNT} />
    </>
  );
}

export default App;
