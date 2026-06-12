'use client'
import { useEffect, useRef } from 'react'
import { spawnParticles } from '@/utils/animations'
import { useJarvixAPI } from '@/hooks/useJarvixAPI'
import Header from '@/components/Header'
import LeftPanel from '@/components/LeftPanel'
import ArcReactor from '@/components/ArcReactor'
import RightPanel from '@/components/RightPanel'
import BottomBar from '@/components/BottomBar'

export default function Home() {
  const particlesRef = useRef<HTMLDivElement>(null)
  const { portfolio, prices, lastIntent, sending, sendCommand } = useJarvixAPI()

  // Spawn particles on mount
  useEffect(() => {
    if (particlesRef.current) spawnParticles(particlesRef.current, 18)
  }, [])

  // Format prices for display
  const fmt = (n?: number, dec = 0) =>
    n != null ? '$' + n.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }) : undefined

  return (
    <>
      {/* Background layers */}
      <div className="bg-grid" />
      <div className="bg-radial" />
      <div className="scanline" />
      <div className="particles" ref={particlesRef} />

      {/* Main shell */}
      <div className="shell">

        <Header />

        <LeftPanel
          totalValue={portfolio?.total_value ?? 100000}
          ethPrice={prices?.ETH ?? 1997.95}
          btcPrice={prices?.BTC ?? 73085}
        />

        {/* Center — Arc Reactor */}
        <div className="center-panel" style={{ position: 'relative', overflow: 'hidden' }}>
          <div className="center-line-top" />
          <ArcReactor 
            btcPrice={fmt(prices?.BTC ?? 73085)}
            ethPrice={fmt(prices?.ETH ?? 1997.95)}
            solPrice={fmt(prices?.SOL ?? 152.40)}
            portfolio={fmt(portfolio?.total_value ?? 100000)}
          />
          <div className="center-line-bottom" />
        </div>

        <RightPanel
          lastIntent={
            lastIntent
              ? {
                  intent:     lastIntent.intent,
                  confidence: lastIntent.confidence,
                  fastPath:   lastIntent.fast_path,
                  source:     lastIntent.source,
                  latency:    lastIntent.latency_ms,
                }
              : undefined
          }
        />

        <BottomBar sendCommand={sendCommand} sending={sending} />

      </div>
    </>
  )
}
