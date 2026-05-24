import React, { useEffect, useState } from 'react';

const TEAM_COLORS = {
  mercedes: 'var(--mercedes)',
  ferrari: 'var(--ferrari)',
  mclaren: 'var(--mclaren)',
  red_bull: 'var(--redbull)',
  alpine: 'var(--alpine)',
  haas: 'var(--haas)',
  racing_bulls: 'var(--racingbulls)',
  aston_martin: 'var(--aston)',
  williams: 'var(--williams)',
  kick_sauber: 'var(--sauber)',
};

const NATIONALITY_CODES = {
  American: 'USA',
  Australian: 'AUS',
  British: 'GBR',
  Canadian: 'CAN',
  Dutch: 'NED',
  Finnish: 'FIN',
  French: 'FRA',
  German: 'GER',
  Italian: 'ITA',
  Japanese: 'JPN',
  Monegasque: 'MON',
  Mexican: 'MEX',
  NewZealander: 'NZL',
  'New Zealander': 'NZL',
  Spanish: 'ESP',
  Thai: 'THA',
};

function formatDriverName(driver) {
  const initial = driver?.givenName ? `${driver.givenName[0]}.` : '';
  return `${initial} ${driver?.familyName || ''}`.trim();
}

function formatNationality(nationality) {
  return NATIONALITY_CODES[nationality] || String(nationality || '').slice(0, 3).toUpperCase();
}

function Standings() {
  const [standings, setStandings] = useState([]);
  const [rounds, setRounds] = useState('');
  const [lastRace, setLastRace] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('https://api.jolpi.ca/ergast/f1/2026/driverStandings.json')
      .then(res => {
        if (!res.ok) {
          throw new Error('Failed to fetch driver standings.');
        }
        return res.json();
      })
      .then(data => {
        const table = data?.MRData?.StandingsTable;
        const list = table?.StandingsLists?.[0];
        const round = list?.round || table?.round || '';
        const raceName = list?.raceName || table?.raceName;
        setRounds(round);
        setStandings((list?.DriverStandings || []).slice(0, 10));

        if (raceName || !round) {
          setLastRace(raceName || `Round ${round}`);
          return null;
        }

        return fetch(`https://api.jolpi.ca/ergast/f1/2026/${round}.json`)
          .then(res => (res.ok ? res.json() : null))
          .then(raceData => {
            setLastRace(raceData?.MRData?.RaceTable?.Races?.[0]?.raceName || `Round ${round}`);
          })
          .catch(() => setLastRace(`Round ${round}`));
      })
      .catch(() => {
        setStandings([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const leaderPoints = Number(standings[0]?.points || 0);

  return (
    <div className="col">
      <div className="col-head">
        <div className="col-num">§ 01</div>
        <div className="col-name">Drivers' <em>Championship</em></div>
        <div className="col-sub">{loading ? 'Loading live standings...' : `Top 10 · After ${rounds} Rounds · ${lastRace}`}</div>
      </div>

      {loading && (
        <div className="driver-row leader" style={{ '--team-color': 'var(--mercedes)', animationDelay: '4.5s' }}>
          <div className="driver-pos">--</div>
          <div className="driver-info">
            <div className="driver-line"><span className="driver-name">Loading standings</span><span className="driver-code" style={{ background: 'var(--mercedes)', color: '#000' }}>...</span></div>
            <div className="driver-team">Live data</div>
          </div>
          <div className="driver-pts-wrap"><div className="driver-pts">--</div><div className="driver-pts-sub">pts</div></div>
        </div>
      )}

      {!loading && standings.map((entry, i) => {
        const driver = entry.Driver || {};
        const constructor = entry.Constructors?.[0] || {};
        const constructorId = constructor.constructorId;
        const teamColor = TEAM_COLORS[constructorId] || 'var(--ink-3)';
        const points = Number(entry.points || 0);
        const gap = leaderPoints - points;

        return (
          <div key={driver.driverId || driver.code || i} className={i === 0 ? 'driver-row leader' : 'driver-row'} style={{ '--team-color': teamColor, animationDelay: `${4.5 + (i * 0.08)}s` }}>
            <div className="driver-pos">{String(entry.position || i + 1).padStart(2, '0')}</div>
            <div className="driver-info">
              <div className="driver-line"><span className="driver-name">{formatDriverName(driver)}</span><span className="driver-code" style={{ background: teamColor, color: constructorId === 'mercedes' ? '#000' : undefined }}>{driver.code}</span></div>
              <div className="driver-team">{constructor.name} · {formatNationality(driver.nationality)}{i > 0 && <> · <span className="gap">−{gap}</span></>}</div>
            </div>
            <div className="driver-pts-wrap"><div className="driver-pts">{points}</div><div className="driver-pts-sub">pts</div></div>
          </div>
        );
      })}
    </div>
  );
}

export default Standings;
