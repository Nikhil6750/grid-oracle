import React, { useState, useEffect } from 'react';
import { getLiveRaceResults } from '../services/api';

function PaddockIntel() {
  const [podium, setPodium] = useState([]);
  const [isLive, setIsLive] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchResults() {
      try {
        const race = await getLiveRaceResults('2026', '4');
        if (race && race.Results && race.Results.length >= 3) {
          setPodium(race.Results.slice(0, 3).map(r => ({
            name: `${r.Driver.givenName.charAt(0)}. ${r.Driver.familyName}`,
            team: r.Constructor.name,
            time: r.Time ? r.Time.time : r.status,
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
        { name: 'A.K. Antonelli', team: 'Mercedes', time: '1:33:19.273', pts: '25', car: '12' },
        { name: 'L. Norris', team: 'McLaren', time: '+3.264s', pts: '18', car: '1' },
        { name: 'O. Piastri', team: 'McLaren', time: '+27.092s', pts: '15', car: '81' },
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
          <span>Miami GP · Miami Autodrome · Result</span>
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
          <div className="news-meta"><span className="news-kicker">Team Orders</span><span className="news-num">01</span></div>
          <h3 className="news-headline">Russell vs Antonelli: Mercedes' civil war reaches boiling point in Canada</h3>
          <p className="news-body">Russell won the Sprint after a controversial clash with Antonelli, who was told to hold position. Wolff now faces his toughest call of the season heading into Sunday's race.</p>
        </article>
        
        <article className="news-item neutral">
          <div className="news-meta"><span className="news-kicker">Title Race</span><span className="news-num">02</span></div>
          <h3 className="news-headline">Antonelli leads by 18 points but Russell is closing fast</h3>
          <p className="news-body">After four rounds, ANT heads RUS by 18 points with Russell on pole for today's Canadian GP. McLaren's Norris is 47 back but showed race pace in Miami.</p>
        </article>

        <article className="news-item neutral">
          <div className="news-meta"><span className="news-kicker">Weather</span><span className="news-num">03</span></div>
          <h3 className="news-headline">Rain chaos predicted for Montreal — Verstappen warns of 'carnage'</h3>
          <p className="news-body">Wet conditions forecast for Sunday's race. Verstappen, who qualified P6, says unpredictable weather could shake up the entire order at Circuit Gilles Villeneuve.</p>
        </article>

        <article className="news-item">
          <div className="news-meta"><span className="news-kicker">Grid</span><span className="news-num">04</span></div>
          <h3 className="news-headline">Hamilton under investigation again after Canadian GP qualifying</h3>
          <p className="news-body">FIA stewards launched multiple post-qualifying investigations including one involving Hamilton. Russell starts P1, Antonelli P2, Norris P3, Piastri P4.</p>
        </article>
      </div>
    </div>
  );
}

export default PaddockIntel;
