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
          <div className="cal-meta" style={{ marginTop: 0 }}>22 Rounds · Mar → Dec 2026</div>
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

            <div className="cal-round">
              <div className="cal-rnum">R08<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇦🇹</div>
              <div className="cal-country">Austria</div>
              <div className="cal-flag-name">Red Bull Ring</div>
              <div className="cal-date">Jun 26-28</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R09<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇬🇧</div>
              <div className="cal-country">UK</div>
              <div className="cal-flag-name">Silverstone</div>
              <div className="cal-date">Jul 03-05</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R10<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇧🇪</div>
              <div className="cal-country">Belgium</div>
              <div className="cal-flag-name">Spa-Francorchamps</div>
              <div className="cal-date">Jul 24-26</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R11<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇭🇺</div>
              <div className="cal-country">Hungary</div>
              <div className="cal-flag-name">Hungaroring</div>
              <div className="cal-date">Jul 31-Aug 02</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R12<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇳🇱</div>
              <div className="cal-country">Netherlands</div>
              <div className="cal-flag-name">Zandvoort</div>
              <div className="cal-date">Aug 28-30</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R13<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇮🇹</div>
              <div className="cal-country">Italy</div>
              <div className="cal-flag-name">Monza</div>
              <div className="cal-date">Sep 04-06</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R14<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇦🇿</div>
              <div className="cal-country">Azerbaijan</div>
              <div className="cal-flag-name">Baku</div>
              <div className="cal-date">Sep 19-21</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R15<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇸🇬</div>
              <div className="cal-country">Singapore</div>
              <div className="cal-flag-name">Marina Bay</div>
              <div className="cal-date">Oct 02-04</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R16<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇺🇸</div>
              <div className="cal-country">USA</div>
              <div className="cal-flag-name">Austin COTA</div>
              <div className="cal-date">Oct 16-18</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R17<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇲🇽</div>
              <div className="cal-country">Mexico</div>
              <div className="cal-flag-name">Mexico City</div>
              <div className="cal-date">Oct 23-25</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R18<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇧🇷</div>
              <div className="cal-country">Brazil</div>
              <div className="cal-flag-name">Interlagos</div>
              <div className="cal-date">Nov 13-15</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R19<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇺🇸</div>
              <div className="cal-country">Las Vegas</div>
              <div className="cal-flag-name">Las Vegas Strip</div>
              <div className="cal-date">Nov 19-21</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R20<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇶🇦</div>
              <div className="cal-country">Qatar</div>
              <div className="cal-flag-name">Lusail</div>
              <div className="cal-date">Nov 28-30</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R21<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇦🇪</div>
              <div className="cal-country">Abu Dhabi</div>
              <div className="cal-flag-name">Yas Marina</div>
              <div className="cal-date">Dec 05-07</div>
            </div>

            <div className="cal-round">
              <div className="cal-rnum">R22<span className="cal-status-dot"></span></div>
              <div className="cal-flag-emoji">🇿🇦</div>
              <div className="cal-country">South Africa</div>
              <div className="cal-flag-name">Kyalami</div>
              <div className="cal-date">Dec 12–14</div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}

export default Calendar;
