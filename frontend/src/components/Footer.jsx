import React, { useState, useEffect } from 'react';

function Footer() {
  const [isColoOpen, setIsColoOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isColoOpen) {
        setIsColoOpen(false);
      }
    };
    
    if (isColoOpen) {
      document.body.classList.add('colo-open');
    } else {
      document.body.classList.remove('colo-open');
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.classList.remove('colo-open');
    };
  }, [isColoOpen]);

  return (
    <>
      <section className="golive-section">
        <div className="golive-card">
          <div className="golive-stripe" aria-hidden="true"></div>
          <div className="golive-left">
            <div className="golive-eyebrow">§ 04 · Race Intel</div>
            <h2 className="golive-title">Built with <em>PitWall AI</em>.</h2>
            <p className="golive-lede">
              Predictions powered by a custom ML pipeline trained on FastF1 data from 2018–2026. 
              Models retrain after every qualifying session. Post-qualifying accuracy: 96.9% AUC.
            </p>
          </div>
          <div className="golive-right">
            
            <div className="golive-step">
              <div className="golive-step-num">01</div>
              <div>
                <div className="golive-step-head">Data <em>· FastF1 + 8 seasons</em></div>
                <div className="golive-step-body">Ingests lap times, qualifying gaps, weather, wet skill, team strategy and driver form from 2018 to present.</div>
              </div>
            </div>

            <div className="golive-step">
              <div className="golive-step-num">02</div>
              <div>
                <div className="golive-step-head">Models <em>· HistGradientBoosting</em></div>
                <div className="golive-step-body">Separate classifiers for podium probability, exact P1/P2/P3 ranking, and top 10 finishers. LeakageGuard prevents data contamination.</div>
              </div>
            </div>

            <div className="golive-step">
              <div className="golive-step-num">03</div>
              <div>
                <div className="golive-step-head">Pipeline <em>· FastAPI + React</em></div>
                <div className="golive-step-body">Predictions served via FastAPI backend. Frontend auto-loads latest prediction on page open.</div>
              </div>
            </div>

            <div className="golive-cta-row">
              <a className="golive-cta golive-cta-ghost" href="https://github.com/Nikhil6750/grid-oracle" target="_blank" rel="noreferrer">GitHub</a>
              <a className="golive-cta golive-cta-ghost" href="https://docs.fastf1.dev/" target="_blank" rel="noreferrer">FastF1</a>
            </div>

          </div>
        </div>
      </section>

      <div className="footer-wrap">
        <footer className="footer">
          <div className="f-note">For Nikhil · eyes only<span className="f-dot"></span>Lights out and away we go</div>
          <div className="f-brand">The <em>Pit Wall</em></div>
        </footer>
        <div className="f-colophon-row">
          <button type="button" className="f-colophon-btn" onClick={() => setIsColoOpen(true)} aria-haspopup="dialog">
            <span>Credits</span>
          </button>
        </div>
      </div>

      <div className={`colophon-modal ${isColoOpen ? 'open' : ''}`} role="dialog" aria-modal="true" hidden={!isColoOpen}>
        <div className="colo-backdrop" onClick={() => setIsColoOpen(false)}></div>
        <div className="colo-card" role="document">
          <button type="button" className="colo-close" onClick={() => setIsColoOpen(false)} aria-label="Close">✕</button>
          <div className="colo-scroll">

            <header className="colo-head">
              <div className="colo-eyebrow">◆ Credits</div>
              <h2 className="colo-title">The <em>Pit Wall</em></h2>
              <p className="colo-sub">Built by Nikhil · F1 fan · ML enthusiast</p>
            </header>

            <div className="colo-rule" aria-hidden="true"></div>

            <section className="colo-author-sec">
              <p className="colo-author-bio">
                I'm <strong>Nikhil</strong>. I built PitWall AI — an ML-powered F1 prediction engine trained on 8 seasons of FastF1 data. This dashboard is the frontend.
              </p>
              <div className="colo-links">
                <a className="colo-btn" href="https://github.com/Nikhil6750/grid-oracle" target="_blank" rel="noreferrer">GitHub · grid-oracle <span className="colo-arr">→</span></a>
              </div>
            </section>

            <div className="colo-rule" aria-hidden="true"></div>

            <section className="colo-tip-sec">
              <div className="colo-author-label">Pit Crew Support</div>
              <h3 className="colo-tip-head">If this made your race weekend, <em>pit us in</em>.</h3>
              <p className="colo-tip-body">No ads, no subscriptions. A small tip keeps the garage lights on.</p>

              <div className="colo-podium">
                <div className="colo-p" data-pos="p10">
                  <div className="colo-p-pos">P10</div>
                  <div className="colo-p-val">₹100</div>
                  <div className="colo-p-lbl">Points finish</div>
                </div>
                <div className="colo-p" data-pos="p3">
                  <div className="colo-p-pos">P3</div>
                  <div className="colo-p-val">₹300</div>
                  <div className="colo-p-lbl">Podium</div>
                </div>
                <div className="colo-p" data-pos="p1">
                  <div className="colo-p-pos">P1</div>
                  <div className="colo-p-val">₹500</div>
                  <div className="colo-p-lbl">Race winner</div>
                </div>
                <div className="colo-p-any">or whatever feels right</div>
              </div>

              <div className="colo-upi">
                <div className="colo-upi-left">
                  <span className="colo-upi-label">UPI</span>
                  <code className="colo-upi-id">7814769892@yescred</code>
                  <div className="colo-upi-scan">Paste into any UPI app · PhonePe · GPay</div>
                </div>
                <div className="colo-upi-qr">
                  <img src="https://pavilion.anirudhgoyal55.workers.dev/assets/upi-qr.png" alt="UPI QR code" loading="lazy" />
                </div>
              </div>
              <p className="colo-tip-sig">Every tip gets a thank-you in the next commit message. No joke.</p>
            </section>

            <div className="colo-rule" aria-hidden="true"></div>

            <p className="colo-disclaimer">
              The Pit Wall is an unofficial fan project. Not affiliated with, endorsed by, or associated with Formula 1, the FIA, FOM, or any team.
            </p>

          </div>
        </div>
      </div>
    </>
  );
}

export default Footer;
