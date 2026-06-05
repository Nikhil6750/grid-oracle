import React, { useEffect, useState } from 'react';
import { getDriverStandings, getNextRace, getLastRaceResult } from '../services/raceService';

function StatsRibbon() {
  const [standings, setStandings] = useState([]);
  const [nextRace, setNextRace] = useState(null);
  const [lastRace, setLastRace] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadStats() {
      const [standingsResult, nextRaceResult, lastRaceResult] = await Promise.allSettled([
        getDriverStandings(),
        getNextRace(),
        getLastRaceResult()
      ]);

      if (!active) return;

      if (standingsResult.status === 'fulfilled') {
        setStandings(standingsResult.value || []);
      }

      if (nextRaceResult.status === 'fulfilled') {
        setNextRace(nextRaceResult.value);
      }

      if (lastRaceResult.status === 'fulfilled') {
        setLastRace(lastRaceResult.value);
      }

      setLoading(false);
    }

    loadStats();

    return () => {
      active = false;
    };
  }, []);

  const formatDate = (date) => {
    if (!date) return '';
    return new Date(`${date}T00:00:00Z`).toLocaleDateString('en-US', {
      month: 'short',
      day: '2-digit',
      timeZone: 'UTC'
    });
  };

  const shortenRaceName = (name) => (name || '').replace(/\s+Grand Prix$/, ' GP');
  const leader = standings[0];
  const second = standings[1];
  const gap = leader && second ? Number(leader.points) - Number(second.points) : 0;
  const lastRaceLocation = [lastRace?.circuitName, lastRace?.locality].filter(Boolean).join(' ');

  return (
    <section className="stats-ribbon">
      <div className="stats-grid">
        <div className="stat">
          <div className="stat-label">Championship Lead</div>
          <div className="stat-big">{loading ? <div className="skeleton-box" style={{ width: '70%' }}></div> : <><em>+{gap}</em> pts</>}</div>
          <div className="stat-sub">{loading ? <div className="skeleton-box" style={{ width: '80%' }}></div> : `${leader?.Driver?.familyName || 'Leader'} over ${second?.Driver?.familyName || 'P2'}`}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Last Race Winner</div>
          <div className="stat-big">{loading ? <div className="skeleton-box" style={{ width: '85%' }}></div> : lastRace?.results?.[0]?.name}</div>
          <div className="stat-sub">{loading ? <div className="skeleton-box" style={{ width: '75%' }}></div> : `${lastRace?.raceName || ''} · ${lastRaceLocation}`}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Next Race</div>
          <div className="stat-big">{loading ? <div className="skeleton-box" style={{ width: '72%' }}></div> : shortenRaceName(nextRace?.name)}<em></em></div>
          <div className="stat-sub">{loading ? <div className="skeleton-box" style={{ width: '70%' }}></div> : `${formatDate(nextRace?.raceDate)} · ${nextRace?.locality || ''}`}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Championship Lead pts</div>
          <div className="stat-big">{loading ? <div className="skeleton-box" style={{ width: '66%' }}></div> : <>P{leader?.position} <em>·</em> +{gap}</>}</div>
          <div className="stat-sub">{loading ? <div className="skeleton-box" style={{ width: '60%' }}></div> : `${leader?.Driver?.familyName || 'Leader'} leads`}</div>
        </div>
      </div>
    </section>
  );
}

export default StatsRibbon;
