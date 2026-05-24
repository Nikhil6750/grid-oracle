import React from 'react';
import Ticker from './components/Ticker';
import Hero from './components/Hero';
import RaceHero from './components/RaceHero';
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
