import React, { useEffect, useRef } from 'react'
import { gsap } from 'gsap'

// TODO: replace with live API
const MOCK = [
  "ANT WINS MONACO · +43 PTS LEAD",
  "HAM P2 — FERRARI STRATEGY PAYS OFF",
  "VER DNF — RED BULL RELIABILITY",
  "NEXT: BARCELONA GP · JUN 12–14",
  "GRID ORACLE: 2/3 EXACT IN MONACO"
]

export default function Ticker() {
  const tickerRef = useRef(null)

  useEffect(() => {
    const el = tickerRef.current
    if (!el) return
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!prefersReducedMotion) {
      gsap.to(el, {
        xPercent: -50,
        ease: "none",
        duration: 30,
        repeat: -1
      })
    }
  }, [])

  return (
    <div className="ticker-wrapper">
      <div className="ticker-content" ref={tickerRef}>
        {[...MOCK, ...MOCK].map((text, i) => (
          <div key={i} className="ticker-item mono-text">
            {text}
          </div>
        ))}
      </div>
    </div>
  )
}
