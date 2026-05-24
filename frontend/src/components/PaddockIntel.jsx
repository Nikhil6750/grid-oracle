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
          <div className="news-meta"><span className="news-kicker">The Story</span><span className="news-num">01</span></div>
          <h3 className="news-headline">Antonelli's rookie surge rewrites Mercedes' championship math</h3>
          <p className="news-body">Three rounds in, the 19-year-old Italian has back-to-back wins and sits atop the drivers' table. Wolff has already shifted team orders mid-weekend.</p>
        </article>
        
        <article className="news-item neutral">
          <div className="news-meta"><span className="news-kicker">Engine Wars</span><span className="news-num">02</span></div>
          <h3 className="news-headline">Red Bull's new PU is down 15hp to Mercedes, paddock sources say</h3>
          <p className="news-body">Despite the full Ford works programme, Red Bull's 2026 power unit appears weakest on the grid. Verstappen's P5 in Japan came from chassis, not pace.</p>
        </article>

        <article className="news-item neutral">
          <div className="news-meta"><span className="news-kicker">Debut</span><span className="news-num">03</span></div>
          <h3 className="news-headline">Cadillac goal is simple: finish races, learn fast, build for 2029</h3>
          <p className="news-body">GM's eleventh team runs Ferrari PUs until its in-house unit is ready. Herta confirmed for four FP1 outings this year.</p>
        </article>

        <article className="news-item">
          <div className="news-meta"><span className="news-kicker">Calendar</span><span className="news-num">04</span></div>
          <h3 className="news-headline">FIA confirms Bahrain and Saudi cancellations, no replacements</h3>
          <p className="news-body">Iran war fallout leaves the season at 23 rounds, Australia to Abu Dhabi. Feeder series affected too.</p>
        </article>
      </div>
    </div>
  );
}

export default PaddockIntel;
