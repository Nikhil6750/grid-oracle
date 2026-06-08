import React, { useEffect } from 'react';
import Ticker from './components/Ticker';
import Hero from './components/Hero';
import RaceHero from './components/RaceHero';
import SessionResults from './components/SessionResults';
import LivePrediction from './components/LivePrediction';
import PredictionPanel from './components/PredictionPanel';
import Calendar from './components/Calendar';
import Standings from './components/Standings';
import PaddockIntel from './components/PaddockIntel';
import StatsRibbon from './components/StatsRibbon';
import Footer from './components/Footer';

function App() {
  // Scroll reveal — content is visible by default; the observer only adds the
  // entrance animation when a block scrolls into view. Safe with no JS.
  useEffect(() => {
    const targets = document.querySelectorAll(
      '.race-hero, .pred-panel, .col, .stats-ribbon, .golive-section, [data-reveal]'
    );
    targets.forEach((el) => el.setAttribute('data-reveal', ''));
    // Arm the hidden start-state only now that JS is confirmed running.
    document.documentElement.classList.add('reveal-on');

    if (!('IntersectionObserver' in window)) {
      targets.forEach((el) => el.classList.add('in-view'));
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('in-view');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
    );

    targets.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <>
      <Ticker />
      <Hero />
      <RaceHero />
      <SessionResults season="2026" round="6" />
      <LivePrediction />
      <PredictionPanel />

      <section className="main-section">
        <div className="main-grid">
          <Standings />
          <Calendar />
          <PaddockIntel />
        </div>
      </section>

      <StatsRibbon />
      <Footer />
    </>
  );
}

export default App;
