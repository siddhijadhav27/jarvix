'use client'
import { useEffect, useRef } from 'react'
import { generateTicks } from '@/utils/animations'

interface ArcReactorProps {
  btcPrice?: string
  ethPrice?: string
  solPrice?: string
  portfolio?: string
  pulseSpeed?: number   // 2s–5s, controlled externally
  pulseColor?: string   // hex color, controlled externally
}

export default function ArcReactor({
  btcPrice = '$73,085',
  ethPrice = '$1,997',
  solPrice = '$152.40',
  portfolio = '$311,342',
  pulseSpeed = 3,
  pulseColor = '#00d4ff',
}: ArcReactorProps) {
  const tickRef = useRef<SVGGElement>(null)

  // Generate tick marks on mount
  useEffect(() => {
    if (tickRef.current) {
      tickRef.current.innerHTML = '' // clear first
      generateTicks(tickRef.current)
    }
  }, [])

  // Update pulse ring styles when props change
  useEffect(() => {
    document.querySelectorAll<HTMLElement>('.pulse-ring').forEach((r) => {
      r.style.animationDuration = pulseSpeed + 's'
      r.style.borderColor = pulseColor
    })
  }, [pulseSpeed, pulseColor])

  return (
    <div className="arc-container">

      {/* Pulse rings — expanding outward */}
      <div className="pulse-ring" />
      <div className="pulse-ring" />
      <div className="pulse-ring" />

      {/* Rotating outer rings */}
      <div className="arc-ring arc-ring-1" />
      <div className="arc-ring arc-ring-2" />
      <div className="arc-ring arc-ring-3" />
      <div className="arc-ring arc-ring-4" />

      {/* Tick marks SVG */}
      <svg className="arc-ticks" viewBox="0 0 248 248">
        <g ref={tickRef} />
      </svg>

      {/* Inner rings */}
      <div className="arc-inner-1" />
      <div className="arc-inner-2" />

      {/* Glowing core */}
      <div className="arc-core" />

      {/* Hexagon */}
      <div className="arc-hex">
        <svg viewBox="0 0 100 100">
          <polygon
            points="50,5 90,27.5 90,72.5 50,95 10,72.5 10,27.5"
            fill="none" stroke="#006688" strokeWidth="1"
            style={{ filter: 'drop-shadow(0 0 4px #00d4ff66)' }}
          />
          <polygon
            points="50,18 78,33 78,67 50,82 22,67 22,33"
            fill="none" stroke="#003344" strokeWidth="1"
          />
        </svg>
      </div>

      {/* JARVIX text */}
      <div className="arc-text">
        <span className="arc-text-main">JARVIX</span>
        <span className="arc-text-sub">ONLINE · READY</span>
      </div>

      {/* Cardinal data points */}
      <div className="arc-data-point" style={{ top: '-22px', left: '50%', transform: 'translateX(-50%)' }}>
        <span className="adp-val">{btcPrice}</span>
        BTC
      </div>
      <div className="arc-data-point" style={{ right: '-58px', top: '50%', transform: 'translateY(-50%)' }}>
        <span className="adp-val">{ethPrice}</span>
        ETH
      </div>
      <div className="arc-data-point" style={{ bottom: '-22px', left: '50%', transform: 'translateX(-50%)' }}>
        <span className="adp-val">{portfolio}</span>
        PORTFOLIO
      </div>
      <div className="arc-data-point" style={{ left: '-58px', top: '50%', transform: 'translateY(-50%)' }}>
        <span className="adp-val">{solPrice}</span>
        SOL
      </div>

    </div>
  )
}
