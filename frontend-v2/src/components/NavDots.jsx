import { useEffect, useState } from 'react';

export default function NavDots({ count }) {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const onChange = (e) => setActive(e.detail);
    window.addEventListener('sectionChange', onChange);
    return () => window.removeEventListener('sectionChange', onChange);
  }, []);

  return (
    <div
      style={{
        position: 'fixed',
        right: '24px',
        top: '50%',
        transform: 'translateY(-50%)',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        zIndex: 100
      }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <button
          key={i}
          aria-label={`Go to section ${i + 1}`}
          onClick={() => window.dispatchEvent(new CustomEvent('gotoSection', { detail: i }))}
          style={{
            width: i === active ? '8px' : '6px',
            height: i === active ? '8px' : '6px',
            borderRadius: '50%',
            background: i === active ? '#e10600' : 'transparent',
            border: i === active ? 'none' : '1px solid rgba(255,255,255,0.6)',
            boxShadow: i === active ? '0 0 8px rgba(225,6,0,0.8)' : 'none',
            padding: 0,
            cursor: 'pointer',
            transition: 'all 0.3s ease'
          }}
        />
      ))}
    </div>
  );
}
