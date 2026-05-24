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
            <div className="golive-eyebrow">§ 04 · Go Live</div>
            <h2 className="golive-title">Make it <em>auto-update</em>.</h2>
            <p className="golive-lede">
              Right now this dashboard is a snapshot — you update the numbers after each race. When you're ready, there are three paths to real-time data pulled straight from the F1 API after every checkered flag.
            </p>
          </div>
          <div className="golive-right">
            
            <div className="golive-step">
              <div className="golive-step-num">01</div>
              <div>
                <div className="golive-step-head">Manual <em>· 2 min after each race</em></div>
                <div className="golive-step-body">
                  Open <code>index.html</code> in any text editor. Find a driver's name (e.g. <code>Antonelli</code>), update the number a few lines below it (e.g. <code>72</code> &rarr; <code>97</code>). Save. Redeploy.
                </div>
              </div>
            </div>

            <div className="golive-step">
              <div className="golive-step-num">02</div>
              <div>
                <div className="golive-step-head">Semi-auto <em>· 30 sec via AI</em></div>
                <div className="golive-step-body">
                  Paste the file into Claude or ChatGPT with this prompt &mdash; it does the rest.
                </div>
                <details className="golive-details">
                  <summary>show the prompt</summary>
                  <pre className="golive-pre">{`Update my F1 dashboard after the [RACE NAME] GP.

New driver standings (top 10):
1. Antonelli — 97
2. Russell — 84
3. Leclerc — 68
...

New constructor totals:
Mercedes 181, Ferrari 124, McLaren ...

Update the countdown to the next race.
Return the COMPLETE HTML in one code block.`}</pre>
                </details>
              </div>
            </div>

            <div className="golive-step">
              <div className="golive-step-num">03</div>
              <div>
                <div className="golive-step-head">Full auto <em>· public API, no manual edits</em></div>
                <div className="golive-step-body">
                  Hook the dashboard to a public F1 data API. Standings update on their own once a race is over.
                </div>
                <details className="golive-details">
                  <summary>show the setup</summary>
                  <p className="golive-detail-p"><strong>Easiest path &middot; Jolpica F1.</strong> Fetch from <code>https://api.jolpi.ca/ergast/f1/current/driverStandings.json</code> and map to your React state.</p>
                  <p className="golive-detail-p"><strong>Python path &middot; FastF1.</strong> Use FastF1 to write a JSON snapshot, commit it via a GitHub Action, and fetch it here.</p>
                </details>
              </div>
            </div>

            <div className="golive-cta-row">
              <a className="golive-cta golive-cta-ghost" href="https://api.jolpi.ca/ergast/" target="_blank" rel="noreferrer">Jolpica F1 API</a>
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
              <p className="colo-sub">First made for my friend Shreya. Now yours, too.</p>
            </header>

            <div className="colo-rule" aria-hidden="true"></div>

            <section className="colo-author-sec">
              <p className="colo-author-bio">
                I'm <strong>Anirudh</strong>. I make dashboards for the things I love — cricket, Formula 1, whatever my friends fall asleep scrolling.
              </p>
              <div className="colo-links">
                <a className="colo-btn" href="https://anirudhgoel.xyz" target="_blank" rel="noreferrer">anirudhgoel.xyz <span className="colo-arr">→</span></a>
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
