import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';

// TODO: replace with live API
const MOCK = [
  { round: '01', country: 'AUS', flag: '🇦🇺', gp: 'AUSTRALIAN', circuit: 'Albert Park Circuit', date: 'Mar 15–17', time: '14:00', status: 'past', winner: 'RUS' },
  { round: '02', country: 'CHN', flag: '🇨🇳', gp: 'CHINESE', circuit: 'Shanghai International Circuit', date: 'Apr 05–07', time: '15:00', status: 'past', winner: 'ANT' },
  { round: '03', country: 'JPN', flag: '🇯🇵', gp: 'JAPANESE', circuit: 'Suzuka International Racing Course', date: 'Apr 19–21', time: '14:00', status: 'past', winner: 'ANT' },
  { round: '04', country: 'USA', flag: '🇺🇸', gp: 'MIAMI', circuit: 'Miami International Autodrome', date: 'May 03–05', time: '16:00', status: 'past', winner: 'ANT' },
  { round: '05', country: 'CAN', flag: '🇨🇦', gp: 'CANADIAN', circuit: 'Circuit Gilles-Villeneuve', date: 'May 17–19', time: '14:00', status: 'past', winner: 'ANT' },
  { round: '06', country: 'MCO', flag: '🇲🇨', gp: 'MONACO', circuit: 'Circuit de Monaco', date: 'May 31–Jun 02', time: '15:00', status: 'past', winner: 'ANT' },
  { round: '07', country: 'ESP', flag: '🇪🇸', gp: 'SPANISH', circuit: 'Circuit de Barcelona-Catalunya', date: 'Jun 12–14', time: '15:00', status: 'next', winner: null },
  { round: '08', country: 'AUT', flag: '🇦🇹', gp: 'AUSTRIAN', circuit: 'Red Bull Ring', date: 'Jun 26–28', time: '15:00', status: 'upcoming' },
  { round: '09', country: 'GBR', flag: '🇬🇧', gp: 'BRITISH', circuit: 'Silverstone Circuit', date: 'Jul 10–12', time: '15:00', status: 'upcoming' },
  { round: '10', country: 'BEL', flag: '🇧🇪', gp: 'BELGIAN', circuit: 'Circuit de Spa-Francorchamps', date: 'Jul 24–26', time: '15:00', status: 'upcoming' },
  { round: '11', country: 'HUN', flag: '🇭🇺', gp: 'HUNGARIAN', circuit: 'Hungaroring', date: 'Aug 07–09', time: '15:00', status: 'upcoming' },
  { round: '12', country: 'NLD', flag: '🇳🇱', gp: 'DUTCH', circuit: 'Circuit Zandvoort', date: 'Aug 21–23', time: '15:00', status: 'upcoming' },
  { round: '13', country: 'ITA', flag: '🇮🇹', gp: 'ITALIAN', circuit: 'Autodromo Nazionale Monza', date: 'Sep 04–06', time: '15:00', status: 'upcoming' },
  { round: '14', country: 'ESP', flag: '🇪🇸', gp: 'MADRID', circuit: 'IFEMA Madrid Circuit', date: 'Sep 18–20', time: '15:00', status: 'upcoming' },
  { round: '15', country: 'AZE', flag: '🇦🇿', gp: 'AZERBAIJAN', circuit: 'Baku City Circuit', date: 'Oct 02–04', time: '15:00', status: 'upcoming' },
  { round: '16', country: 'SGP', flag: '🇸🇬', gp: 'SINGAPORE', circuit: 'Marina Bay Street Circuit', date: 'Oct 16–18', time: '20:00', status: 'upcoming' },
  { round: '17', country: 'USA', flag: '🇺🇸', gp: 'UNITED STATES', circuit: 'Circuit of the Americas', date: 'Oct 30–Nov 01', time: '14:00', status: 'upcoming' },
  { round: '18', country: 'MEX', flag: '🇲🇽', gp: 'MEXICO CITY', circuit: 'Autódromo Hermanos Rodríguez', date: 'Nov 06–08', time: '14:00', status: 'upcoming' },
  { round: '19', country: 'BRA', flag: '🇧🇷', gp: 'SÃO PAULO', circuit: 'Autódromo José Carlos Pace', date: 'Nov 20–22', time: '14:00', status: 'upcoming' },
  { round: '20', country: 'USA', flag: '🇺🇸', gp: 'LAS VEGAS', circuit: 'Las Vegas Strip Circuit', date: 'Nov 26–28', time: '22:00', status: 'upcoming' },
  { round: '21', country: 'QAT', flag: '🇶🇦', gp: 'QATAR', circuit: 'Lusail International Circuit', date: 'Dec 04–06', time: '20:00', status: 'upcoming' },
  { round: '22', country: 'ARE', flag: '🇦🇪', gp: 'ABU DHABI', circuit: 'Yas Marina Circuit', date: 'Dec 18–20', time: '17:00', status: 'upcoming' }
];

export default function Calendar() {
  const containerRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.cal-card', {
        opacity: 0,
        x: 40,
        duration: 0.6,
        stagger: 0.05,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: containerRef.current,
          start: 'top 80%'
        }
      });
    }, containerRef);

    if (scrollRef.current) {
      setTimeout(() => {
        const nextCard = scrollRef.current.querySelector('.cal-status-next');
        if (nextCard) {
          const scrollPos = nextCard.offsetLeft - window.innerWidth / 2 + 110;
          scrollRef.current.scrollTo({ left: scrollPos, behavior: 'smooth' });
        }
      }, 500);
    }

    return () => ctx.revert();
  }, []);

  const handleWheel = (e) => {
    if (scrollRef.current) {
      // Map vertical scroll to horizontal
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        scrollRef.current.scrollLeft += e.deltaY;
      }
    }
  };

  return (
    <section className="calendar-section reveal" ref={containerRef}>
      <h3 className="section-title">RACE CALENDAR</h3>
      
      <div className="cal-scroll-container" ref={scrollRef} onWheel={handleWheel}>
        {MOCK.map((race, i) => (
          <div key={i} className={`cal-card g-card cal-status-${race.status}`}>
            {race.status === 'next' && <div className="next-badge">NEXT RACE</div>}
            
            <div className="cal-round">R{race.round} · {race.country}</div>
            <div className="cal-flag">{race.flag}</div>
            
            <div className="cal-name">
              {race.gp}<br/>GRAND PRIX
            </div>
            
            <div className="cal-circuit">{race.circuit}</div>
            
            <div className="cal-bottom">
              <div className="cal-date">{race.date}</div>
              <div className="cal-time">{race.time} local</div>
            </div>

            {race.status === 'past' && (
              <div className="cal-win-badge">WIN: {race.winner}</div>
            )}
          </div>
        ))}
      </div>

      <style jsx>{`
        .calendar-section {
          width: 100vw;
          margin-left: calc(-50vw + 50%);
          margin-top: 80px;
          padding: 40px 0;
        }
        .section-title {
          padding: 0 var(--section-pad);
          margin-bottom: 32px;
        }
        .cal-scroll-container {
          display: flex;
          gap: 16px;
          padding: 20px var(--section-pad) 40px;
          overflow-x: auto;
          scroll-behavior: auto; /* smooth handled by react */
          -webkit-overflow-scrolling: touch;
        }
        
        /* Custom scrollbar */
        .cal-scroll-container::-webkit-scrollbar {
          height: 3px;
        }
        .cal-scroll-container::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.06);
        }
        .cal-scroll-container::-webkit-scrollbar-thumb {
          background: linear-gradient(90deg, var(--red), var(--red-hot));
          border-radius: 3px;
        }

        .cal-card {
          flex: 0 0 220px;
          height: 280px;
          padding: 20px;
          display: flex;
          flex-direction: column;
          position: relative;
        }
        
        .cal-status-past {
          opacity: 0.45;
        }
        .cal-status-next {
          border: 1px solid rgba(225,6,0,0.5);
          background: rgba(225,6,0,0.06);
          box-shadow: 0 0 30px rgba(225,6,0,0.1);
        }
        
        .next-badge {
          position: absolute;
          top: -12px;
          left: 20px;
          background: var(--red);
          color: var(--white);
          font-family: var(--font-mono);
          font-size: 9px;
          padding: 4px 8px;
          letter-spacing: 0.1em;
          border-radius: 4px;
        }
        .cal-win-badge {
          position: absolute;
          bottom: -12px;
          right: 20px;
          background: rgba(225,6,0,0.8);
          color: var(--white);
          font-family: var(--font-mono);
          font-size: 9px;
          padding: 4px 8px;
          letter-spacing: 0.1em;
          border-radius: 50px;
        }

        .cal-round {
          font-family: var(--font-mono);
          font-size: 9px;
          color: rgba(255,255,255,0.4);
          letter-spacing: 0.1em;
          margin-bottom: 12px;
        }
        .cal-flag {
          font-size: 32px;
          line-height: 1;
          margin-bottom: 16px;
        }
        .cal-name {
          font-family: var(--font-display);
          font-size: 28px;
          line-height: 0.9;
          color: var(--white);
          margin-bottom: 8px;
        }
        .cal-circuit {
          font-family: var(--font-body);
          font-size: 11px;
          color: rgba(255,255,255,0.4);
          line-height: 1.4;
          flex-grow: 1;
        }
        .cal-bottom {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .cal-date {
          font-family: var(--font-mono);
          font-size: 12px;
          color: var(--white);
        }
        .cal-time {
          font-family: var(--font-mono);
          font-size: 11px;
          color: rgba(255,255,255,0.4);
        }
      `}</style>
    </section>
  );
}
