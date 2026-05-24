import React from 'react';

function Ticker() {
  const items = [
    { sym: 'WDC', val: 'ANTONELLI', pts: '97 pts' },
    { sym: 'WCC', val: 'MERCEDES', pts: '181 pts' },
    { sym: 'NEXT', val: 'CANADA GP', pts: 'MAY 24' },
    { sym: 'MIAMI', val: 'ANTONELLI', pts: 'WINNER' },
    { sym: 'VER', val: 'P7 MIAMI', pts: '+5 places' },
    { sym: 'MCLAREN', val: 'UPGRADE', pts: 'WORKING' },
    { sym: 'FL', val: 'RUSSELL', pts: 'MIAMI' },
    { sym: 'GRID ORACLE', val: 'LIVE', pts: 'BACKEND READY' },
  ];

  const renderTick = (it, i) => (
    <React.Fragment key={i}>
      <span className="tick">
        <span className="sym">{it.sym}</span> 
        <span className="val">{it.val}</span> 
        <span className="pts">{it.pts}</span>
      </span>
      <span className="tick tick-dot">◆</span>
    </React.Fragment>
  );

  return (
    <div className="ticker-wrap">
      <div className="ticker-track">
        {items.map(renderTick)}
        {items.map((it, i) => renderTick(it, i + items.length))}
      </div>
    </div>
  );
}

export default Ticker;
