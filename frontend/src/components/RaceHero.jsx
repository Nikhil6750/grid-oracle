import React, { useState, useEffect } from 'react';
import { getNextRace } from '../services/raceService';

function RaceHero() {
  const [cd, setCd] = useState({ d: '00', h: '00', m: '00', s: '00' });
  const [race, setRace] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getNextRace()
      .then(setRace)
      .catch(() => setRace(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!race?.raceDateTime) return;

    const target = race.raceDateTime.getTime();
    const pad = (n) => String(n).padStart(2, '0');

    const tick = () => {
      const diff = target - Date.now();
      if (diff <= 0) {
        setCd({ d: '00', h: '00', m: '00', s: '00' });
        return;
      }
      setCd({
        d: pad(Math.floor(diff / 86400000)),
        h: pad(Math.floor((diff % 86400000) / 3600000)),
        m: pad(Math.floor((diff % 3600000) / 60000)),
        s: pad(Math.floor((diff % 60000) / 1000))
      });
    };

    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [race]);

  const formatDate = (date) => {
    if (!date) return '';
    const parsed = new Date(`${date}T00:00:00Z`);
    return parsed.toLocaleDateString('en-US', { month: 'short', day: '2-digit', timeZone: 'UTC' });
  };

  const raceName = race?.name || 'Loading Grand Prix';
  const cityName = raceName.replace(/\s+Grand Prix$/, '');
  const raceTitle = raceName.endsWith('Grand Prix') ? 'Grand Prix' : '';
  const roundPadded = race?.round ? String(race.round).padStart(2, '0') : '00';
  const dateRange = race ? `${formatDate(race.fp1Date || race.raceDate)}–${formatDate(race.raceDate)}` : 'Loading';

  return (
    <section className="race-hero">
      <div className="race-block">
        <div className="race-grid">
          <div className="race-left">
            <div className="race-meta-row">
              <span className="race-round">◆ Round {roundPadded} · Up Next</span>
              <span className="race-flag-big">{loading ? '🏁' : race?.flag}</span>
            </div>
            <h2 className="race-name">{loading ? 'Loading' : cityName} <em>{loading ? 'Race' : raceTitle}</em></h2>
            <div className="race-circuit"><strong>{loading ? 'Fetching next race' : race?.circuitName}</strong> · {loading ? 'Please wait' : race?.locality}</div>
            <div className="race-circuit">Round {loading ? '0' : race?.round} of 22 · {loading ? '0' : race?.laps} laps · {loading ? '0.000' : Number(race?.distance).toFixed(3)} km · {dateRange}</div>
          </div>

          <div className="race-right">
            <div className="countdown-label">Lights Out In</div>
            <div className="countdown">
              <div className="cd-cell"><div className="cd-num">{cd.d}</div><div className="cd-label">Days</div></div>
              <div className="cd-cell"><div className="cd-num">{cd.h}</div><div className="cd-label">Hours</div></div>
              <div className="cd-cell"><div className="cd-num">{cd.m}</div><div className="cd-label">Mins</div></div>
              <div className="cd-cell"><div className="cd-num">{cd.s}</div><div className="cd-label">Secs</div></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default RaceHero;
