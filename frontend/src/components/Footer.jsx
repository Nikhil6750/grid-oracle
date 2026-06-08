import React from 'react';

function Footer() {
  return (
    <>
      <section className="golive-section" data-reveal>
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
              <a className="golive-cta golive-cta-ghost" href="https://github.com/Nikhil6750/grid-oracle" target="_blank" rel="noreferrer">GitHub →</a>
              <a className="golive-cta golive-cta-ghost" href="https://docs.fastf1.dev/" target="_blank" rel="noreferrer">FastF1</a>
            </div>

          </div>
        </div>
      </section>

      <div className="footer-wrap">
        <footer className="footer">
          <div className="f-note">Built by Nikhil<span className="f-dot"></span>Lights out and away we go</div>
          <div className="f-brand">Pit<em>Wall</em> AI · 2026</div>
        </footer>
      </div>
    </>
  );
}

export default Footer;
