import React from 'react';
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
  return (
    <>
      <Ticker />
      <Hero />
      <RaceHero />
      <SessionResults season="2026" round="6" />
      <LivePrediction season="2026" round="6" />
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
