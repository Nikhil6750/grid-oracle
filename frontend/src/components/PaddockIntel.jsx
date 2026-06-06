import React, { useState, useEffect } from 'react';
import { getLastRaceResult } from '../services/raceService';

function PaddockIntel() {
  const [podium, setPodium] = useState([]);
  const [lastRace, setLastRace] = useState(null);
  const [isLive, setIsLive] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchResults() {
      try {
        const race = await getLastRaceResult();
        if (race && race.results && race.results.length >= 3) {
          setLastRace(race);
          setPodium(race.results.slice(0, 3).map(r => ({
            name: r.name,
            team: r.team,
            time: r.time,
            pts: r.points,
            car: r.number
          })));
          setIsLive(true);
        } else {
          setFallback();
        }
      } catch (err) {
        setFallback();
      } finally {
        setLoading(false);
      }
    }

    function setFallback() {
      setIsLive(false);
      setPodium([
        { name: 'K. Antonelli', team: 'Mercedes', time: '1:41:32.000', pts: '25', car: '12' },
        { name: 'L. Hamilton', team: 'Ferrari', time: '+5.2s', pts: '18', car: '44' },
        { name: 'M. Verstappen', team: 'Red Bull', time: '+12.8s', pts: '15', car: '1' },
      ]);
    }

    fetchResults();
  }, []);

  return (
    <div className="col">
      <div className="col-head">
        <div className="col-num">§ 03</div>
        <div className="col-name">Paddock <em>Intel</em></div>
        <div className="col-sub">Last Race · Top Stories</div>
      </div>

      <div className="podium-block">
        <div className="podium-head" style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>{lastRace ? `${lastRace.raceName} · ${lastRace.circuitName} · Result` : 'Last Race · Result'}</span>
          {!isLive && !loading && <span style={{ color: 'var(--ink-3)', fontSize: '8px', background: 'rgba(0,0,0,0.05)', padding: '2px 4px' }}>STATIC FALLBACK</span>}
        </div>
        <div className="podium-list">
          {loading ? (
            <div style={{ color: 'var(--ink-3)', fontSize: '11px', padding: '10px 0' }}>Fetching live results...</div>
          ) : (
            podium.map((p, i) => (
              <div key={i} className={`pod-row p${i + 1}`}>
                <div className="pod-badge">P{i + 1}</div>
                <div>
                  <div className="pod-driver-name">{p.name}</div>
                  <div className="pod-driver-team">{p.team} · #{p.car} · {p.pts} pts</div>
                </div>
                <div className="pod-time">{p.time}</div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="news-block">
        <article className="news-item lead">
          <div className="news-meta"><span className="news-kicker">Title Race</span><span className="news-num">01</span></div>
          <h3 className="news-headline">Antonelli extends lead to 43 points after dominant Canadian GP win</h3>
          <p className="news-body">Kimi Antonelli claimed his fourth win of 2026 in wet Montreal conditions, extending his championship lead over Russell who finished outside the podium.</p>
        </article>
        
        <article className="news-item neutral">
          <div className="news-meta"><span className="news-kicker">Monaco Preview</span><span className="news-num">02</span></div>
          <h3 className="news-headline">Hamilton eyeing back-to-back podiums heading into Monaco</h3>
          <p className="news-body">Lewis Hamilton finished P2 in Canada and arrives at Monte Carlo with strong momentum. Ferrari's strategy team believe the narrow streets suit their 2026 package.</p>
        </article>

        <article className="news-item neutral">
          <div className="news-meta"><span className="news-kicker">Weather</span><span className="news-num">03</span></div>
          <h3 className="news-headline">Light showers possible in Monaco — strategy could be decisive</h3>
          <p className="news-body">Early forecasts suggest mild temperatures in the mid-20s with possible light drizzle during practice and qualifying at Circuit de Monaco.</p>
        </article>

        <article className="news-item">
          <div className="news-meta"><span className="news-kicker">Grid Oracle</span><span className="news-num">04</span></div>
          <h3 className="news-headline">PitWall AI Monaco prediction: HAM wins, ANT P2, LEC P3</h3>
          <p className="news-body">Post-qualifying model gives HAM 53% podium probability. Monaco's narrow streets favour race craft over outright pace — Hamilton's 6 Monaco wins weigh heavily in the model.</p>
        </article>
      </div>
    </div>
  );
}

export default PaddockIntel;
