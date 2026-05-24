import React, { useEffect, useRef } from 'react';

function Calendar() {
  const stripRef = useRef(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (stripRef.current) {
        const next = stripRef.current.querySelector('.cal-round.next');
        if (next) {
          stripRef.current.scrollTo({ left: next.offsetLeft - 60, behavior: 'smooth' });
        }
      }
    }, 5000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="col" style={{ gridColumn: 'span 2' }}>
      <div className="col-head">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <div>
            <div className="col-num">§ 02</div>
            <div className="col-name">Season <em>Calendar</em></div>
          </div>
          <div className="cal-meta" style={{ marginTop: 0 }}>23 Rounds · Mar → Dec 2026</div>
        </div>
      </div>

      <div style={{ padding: '24px' }}>
        <div className="cal-strip-wrap">
          <div className="cal-progress-track">
            <div className="cal-progress-fill" style={{ width: '17.4%' }}></div>
          </div>
          <div className="cal-strip" id="calStrip" ref={stripRef}>
            
            <div className="cal-round done">
              <div className="cal-rnum">R01<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇦🇺</div>
              <div className="cal-country">Australia</div>
              <div className="cal-flag-name">Albert Park</div>
              <div className="cal-date">Mar 06–08</div>
              <div className="cal-winner">G. Russell</div>
            </div>
            
            <div className="cal-round done">
              <div className="cal-rnum">R02<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇨🇳</div>
              <div className="cal-country">China</div>
              <div className="cal-flag-name">Shanghai</div>
              <div className="cal-date">Mar 13–15</div>
              <div className="cal-winner">K. Antonelli</div>
            </div>
            
            <div className="cal-round done">
              <div className="cal-rnum">R03<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇯🇵</div>
              <div className="cal-country">Japan</div>
              <div className="cal-flag-name">Suzuka</div>
              <div className="cal-date">Mar 27–29</div>
              <div className="cal-winner">K. Antonelli</div>
            </div>
            
            <div className="cal-round done">
              <div className="cal-rnum">R04<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇺🇸</div>
              <div className="cal-country">USA</div>
              <div className="cal-flag-name">Miami</div>
              <div className="cal-date">May 01–03</div>
              <div className="cal-winner">K. Antonelli</div>
            </div>
            
            <div className="cal-round next">
              <div className="cal-rnum">R05 · NEXT<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇨🇦</div>
              <div className="cal-country">Canada</div>
              <div className="cal-flag-name">Montreal</div>
              <div className="cal-date">May 22–24</div>
            </div>
            
            <div className="cal-round">
              <div className="cal-rnum">R06<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇲🇨</div>
              <div className="cal-country">Monaco</div>
              <div className="cal-flag-name">Monte Carlo</div>
              <div className="cal-date">Jun 05–07</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R07<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇪🇸</div>
              <div className="cal-country">Spain</div>
              <div className="cal-flag-name">Barcelona</div>
              <div className="cal-date">Jun 12–14</div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}

export default Calendar;
