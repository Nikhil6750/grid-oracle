import React, { useEffect, useRef, useState } from 'react';
import { getFullSeasonSchedule, getLastRaceResult, COUNTRY_FLAGS } from '../services/raceService';

function Calendar() {
  const stripRef = useRef(null);
  const [schedule, setSchedule] = useState([]);
  const [lastResult, setLastResult] = useState(null);

  useEffect(() => {
    let active = true;

    async function loadCalendar() {
      const [scheduleResult, resultResult] = await Promise.allSettled([
        getFullSeasonSchedule(),
        getLastRaceResult()
      ]);

      if (!active) return;

      if (scheduleResult.status === 'fulfilled') {
        setSchedule(scheduleResult.value || []);
      }

      if (resultResult.status === 'fulfilled') {
        setLastResult(resultResult.value);
      }
    }

    loadCalendar();

    return () => {
      active = false;
    };
  }, []);

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
  }, [schedule]);

  const parseDate = (date) => {
    const [year, month, day] = date.split('-').map(Number);
    return new Date(year, month - 1, day);
  };

  const formatMonth = (date) => {
    if (!date) return '';
    return parseDate(date).toLocaleDateString('en-US', { month: 'short' });
  };

  const formatDateRange = (race) => {
    const start = race.FirstPractice?.date || race.date;
    const end = race.date;
    const startDate = parseDate(start);
    const endDate = parseDate(end);
    const month = startDate.toLocaleDateString('en-US', { month: 'short' });
    const startDay = String(startDate.getDate()).padStart(2, '0');
    const endDay = String(endDate.getDate()).padStart(2, '0');
    return `${month} ${startDay}-${endDay}`;
  };

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const nextRace = schedule.find((race) => parseDate(race.date) >= today);
  const nextRound = nextRace ? parseInt(nextRace.round, 10) : null;
  const doneCount = schedule.filter((race) => parseDate(race.date) < today).length;
  const progressWidth = schedule.length ? `${((doneCount / schedule.length) * 100).toFixed(1)}%` : '0%';
  const seasonYear = schedule[0]?.date?.slice(0, 4) || '';
  const calMeta = schedule.length
    ? `${schedule.length} Rounds · ${formatMonth(schedule[0].date)} → ${formatMonth(schedule[schedule.length - 1].date)} ${seasonYear}`
    : 'Loading Calendar';

  return (
    <div className="col" style={{ gridColumn: 'span 2' }}>
      <div className="col-head">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <div>
            <div className="col-num">§ 02</div>
            <div className="col-name">Season <em>Calendar</em></div>
          </div>
          <div className="cal-meta" style={{ marginTop: 0 }}>{calMeta}</div>
        </div>
      </div>

      <div style={{ padding: '24px' }}>
        <div className="cal-strip-wrap">
          <div className="cal-progress-track">
            <div className="cal-progress-fill" style={{ width: progressWidth }}></div>
          </div>
          <div className="cal-strip" id="calStrip" ref={stripRef}>
            {schedule.map((race) => {
              const round = parseInt(race.round, 10);
              const isDone = parseDate(race.date) < today;
              const isNext = round === nextRound;
              const className = isDone ? 'cal-round done' : isNext ? 'cal-round next' : 'cal-round';
              const country = race.Circuit?.Location?.country || '';
              const winner = lastResult?.round === round ? lastResult.results?.[0]?.name : null;

              return (
                <div key={race.round} className={className}>
                  <div className="cal-rnum">R{String(round).padStart(2, '0')}{isNext ? ' · NEXT' : ''}<span className="cal-status-dot"></span></div>
                  <div className="cal-flag-emoji">{COUNTRY_FLAGS[country] || '🏁'}</div>
                  <div className="cal-country">{country}</div>
                  <div className="cal-flag-name">{race.Circuit?.circuitName}</div>
                  <div className="cal-date">{formatDateRange(race)}</div>
                  {isDone && winner && <div className="cal-winner">{winner}</div>}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Calendar;
