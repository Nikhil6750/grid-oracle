import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import F1Logo from '../assets/f1-logo.svg'

const SplashScreen = ({ onDone }) => {
  const splashRef = useRef(null)
  const logoRef = useRef(null)

  useEffect(() => {
    // TEMP: force splash replay for testing — remove after confirming
    sessionStorage.removeItem('splashShown')

    if (sessionStorage.getItem('splashShown')) {
      onDone()
      return
    }

    gsap.set('.splash-logo', { scale: 0.9, opacity: 0 })

    const tl = gsap.timeline({
      onComplete: () => {
        sessionStorage.setItem('splashShown', '1')
        onDone()
      }
    })

    // Logo fades in with electric glow
    tl.to('.splash-logo', {
      scale: 1,
      opacity: 1,
      duration: 0.6,
      ease: 'power3.out'
    })
    // Quick bright pulse (yoyo brings it back to the resting glow)
    .to('.splash-f1-img', {
      filter: 'sepia(1) saturate(10) hue-rotate(320deg) brightness(2) drop-shadow(0 0 60px rgba(255,36,0,1)) drop-shadow(0 0 120px rgba(255,36,0,0.6))',
      duration: 0.1,
      yoyo: true,
      repeat: 1,
      ease: 'power1.inOut'
    }, '+=0.2')
    // Hold
    .to({}, { duration: 0.8 })
    // Morph out
    .to('.splash-logo', {
      scale: 1.6,
      opacity: 0,
      duration: 0.5,
      ease: 'power2.in'
    })
    .to('.splash-root', {
      opacity: 0,
      duration: 0.3
    })

    return () => tl.kill()
  }, [])

  return (
    <div ref={splashRef} className="splash-root">
      <div className="splash-bg-glow" />
      <div ref={logoRef} className="splash-logo">
        <img src={F1Logo} alt="F1" className="splash-f1-img" />
      </div>
    </div>
  )
}

export default SplashScreen
