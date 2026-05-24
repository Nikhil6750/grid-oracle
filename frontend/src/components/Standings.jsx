import React from 'react';

function Standings() {
  return (
    <div className="col">
      <div className="col-head">
        <div className="col-num">§ 01</div>
        <div className="col-name">Drivers' <em>Championship</em></div>
        <div className="col-sub">Top 10 · After 4 Rounds · Miami GP</div>
      </div>

      <div className="driver-row leader" style={{ '--team-color': 'var(--mercedes)', animationDelay: '4.5s' }}>
        <div className="driver-pos">01</div>
        <div className="driver-info">
          <div className="driver-line"><span className="driver-name">K. Antonelli</span><span className="driver-code" style={{ background: 'var(--mercedes)', color: '#000' }}>ANT</span></div>
          <div className="driver-team">Mercedes · ITA</div>
        </div>
        <div className="driver-pts-wrap"><div className="driver-pts">72</div><div className="driver-pts-sub">pts</div></div>
      </div>
      <div className="driver-row" style={{ '--team-color': 'var(--mercedes)', animationDelay: '4.58s' }}>
        <div className="driver-pos">02</div>
        <div className="driver-info">
          <div className="driver-line"><span className="driver-name">G. Russell</span><span className="driver-code" style={{ background: 'var(--mercedes)', color: '#000' }}>RUS</span></div>
          <div className="driver-team">Mercedes · GBR · <span className="gap">−9</span></div>
        </div>
        <div className="driver-pts-wrap"><div className="driver-pts">63</div><div className="driver-pts-sub">pts</div></div>
      </div>
      <div className="driver-row" style={{ '--team-color': 'var(--ferrari)', animationDelay: '4.66s' }}>
        <div className="driver-pos">03</div>
        <div className="driver-info">
          <div className="driver-line"><span className="driver-name">C. Leclerc</span><span className="driver-code" style={{ background: 'var(--ferrari)' }}>LEC</span></div>
          <div className="driver-team">Ferrari · MON · <span className="gap">−23</span></div>
        </div>
        <div className="driver-pts-wrap"><div className="driver-pts">49</div><div className="driver-pts-sub">pts</div></div>
      </div>
      <div className="driver-row" style={{ '--team-color': 'var(--ferrari)', animationDelay: '4.74s' }}>
        <div className="driver-pos">04</div>
        <div className="driver-info">
          <div className="driver-line"><span className="driver-name">L. Hamilton</span><span className="driver-code" style={{ background: 'var(--ferrari)' }}>HAM</span></div>
          <div className="driver-team">Ferrari · GBR · <span className="gap">−31</span></div>
        </div>
        <div className="driver-pts-wrap"><div className="driver-pts">41</div><div className="driver-pts-sub">pts</div></div>
      </div>
      <div className="driver-row" style={{ '--team-color': 'var(--mclaren)', animationDelay: '4.82s' }}>
        <div className="driver-pos">05</div>
        <div className="driver-info">
          <div className="driver-line"><span className="driver-name">L. Norris</span><span className="driver-code" style={{ background: 'var(--mclaren)' }}>NOR</span></div>
          <div className="driver-team">McLaren · GBR · <span className="gap">−47</span></div>
        </div>
        <div className="driver-pts-wrap"><div className="driver-pts">25</div><div className="driver-pts-sub">pts</div></div>
      </div>
      <div className="driver-row" style={{ '--team-color': 'var(--mclaren)', animationDelay: '4.90s' }}>
        <div className="driver-pos">06</div>
        <div className="driver-info">
          <div className="driver-line"><span className="driver-name">O. Piastri</span><span className="driver-code" style={{ background: 'var(--mclaren)' }}>PIA</span></div>
          <div className="driver-team">McLaren · AUS · <span className="gap">−51</span></div>
        </div>
        <div className="driver-pts-wrap"><div className="driver-pts">21</div><div className="driver-pts-sub">pts</div></div>
      </div>
      <div className="driver-row" style={{ '--team-color': 'var(--haas)', animationDelay: '4.98s' }}>
        <div className="driver-pos">07</div>
        <div className="driver-info">
          <div className="driver-line"><span className="driver-name">O. Bearman</span><span className="driver-code" style={{ background: '#4a4a4a' }}>BEA</span></div>
          <div className="driver-team">Haas · GBR · <span className="gap">−55</span></div>
        </div>
        <div className="driver-pts-wrap"><div className="driver-pts">17</div><div className="driver-pts-sub">pts</div></div>
      </div>
      <div className="driver-row" style={{ '--team-color': 'var(--alpine)', animationDelay: '5.06s' }}>
        <div className="driver-pos">08</div>
        <div className="driver-info">
          <div className="driver-line"><span className="driver-name">P. Gasly</span><span className="driver-code" style={{ background: 'var(--alpine)' }}>GAS</span></div>
          <div className="driver-team">Alpine · FRA · <span className="gap">−57</span></div>
        </div>
        <div className="driver-pts-wrap"><div className="driver-pts">15</div><div className="driver-pts-sub">pts</div></div>
      </div>
      <div className="driver-row" style={{ '--team-color': 'var(--redbull)', animationDelay: '5.14s' }}>
        <div className="driver-pos">09</div>
        <div className="driver-info">
          <div className="driver-line"><span className="driver-name">M. Verstappen</span><span className="driver-code" style={{ background: 'var(--redbull)' }}>VER</span></div>
          <div className="driver-team">Red Bull · NED · <span className="gap">−60</span></div>
        </div>
        <div className="driver-pts-wrap"><div className="driver-pts">12</div><div className="driver-pts-sub">pts</div></div>
      </div>
      <div className="driver-row" style={{ '--team-color': 'var(--racingbulls)', animationDelay: '5.22s' }}>
        <div className="driver-pos">10</div>
        <div className="driver-info">
          <div className="driver-line"><span className="driver-name">L. Lawson</span><span className="driver-code" style={{ background: 'var(--racingbulls)' }}>LAW</span></div>
          <div className="driver-team">Racing Bulls · NZL · <span className="gap">−62</span></div>
        </div>
        <div className="driver-pts-wrap"><div className="driver-pts">10</div><div className="driver-pts-sub">pts</div></div>
      </div>
    </div>
  );
}

export default Standings;
