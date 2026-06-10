'use client'
import { useEffect, useRef } from 'react'
import { countUp } from '@/utils/animations'
import DataRow from './DataRow'

interface LeftPanelProps {
  totalValue?: number
  ethPrice?: number
  btcPrice?: number
}

function MiniBar({ label, value }: { label: string; value: number }) {
  const fillRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const t = setTimeout(() => {
      if (fillRef.current) fillRef.current.style.width = value + '%'
    }, 900)
    return () => clearTimeout(t)
  }, [value])

  return (
    <div className="mini-bar-wrap" style={{ marginTop: '10px' }}>
      <div className="mini-bar-label">
        <span>{label}</span>
        <span style={{ color: 'var(--c)' }}>{value}%</span>
      </div>
      <div className="mini-bar">
        <div className="mini-bar-fill" ref={fillRef} style={{ width: '0%' }} />
      </div>
    </div>
  )
}

export default function LeftPanel({
  totalValue = 100000,
  ethPrice = 1997.95,
  btcPrice = 73085,
}: LeftPanelProps) {
  const totalRef = useRef<HTMLDivElement>(null)
  const ethRef   = useRef<HTMLDivElement>(null)
  const btcRef   = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const t = setTimeout(() => {
      if (totalRef.current) countUp(totalRef.current, String(totalValue))
      if (ethRef.current)   countUp(ethRef.current, String(ethPrice), '$', 1800)
      if (btcRef.current)   countUp(btcRef.current, String(btcPrice), '$', 1700)
    }, 400)
    return () => clearTimeout(t)
  }, [totalValue, ethPrice, btcPrice])

  return (
    <div className="left-panel">

      {/* Portfolio */}
      <div className="bracket" style={{ padding: '12px' }}>
        <div className="sec-title">portfolio</div>
        <div className="port-card">
          <div className="port-label">TOTAL VALUE · DEMO</div>
          <div className="port-val" ref={totalRef} style={{ fontSize: '1.3rem' }}>$0</div>
          <div className="port-change up">▲ +2.4% · TODAY</div>
        </div>
        <div className="port-card" style={{ marginTop: '8px' }}>
          <div className="port-label">ETH · ETHEREUM</div>
          <div className="port-val" ref={ethRef} style={{ fontSize: '1rem' }}>$0</div>
          <div className="port-change up">▲ +1.08%</div>
        </div>
        <div className="port-card" style={{ marginTop: '8px' }}>
          <div className="port-label">BTC · BITCOIN</div>
          <div className="port-val" ref={btcRef} style={{ fontSize: '1rem' }}>$0</div>
          <div className="port-change up">▲ +0.29%</div>
        </div>
      </div>

      {/* Market Intel */}
      <div className="bracket" style={{ padding: '12px' }}>
        <div className="sec-title">market intel</div>
        <DataRow label="BTC DOMINANCE" value="54.2%" />
        <DataRow label="FEAR & GREED"  value="41 · FEAR" status="warn" />
        <DataRow label="24H VOLUME"    value="$94.3B" />
        <DataRow label="GLOBAL MCAP"   value="$2.41T" />
        <DataRow label="ETH GAS"       value="12 GWEI" />
        <DataRow label="FUNDING RATE"  value="+0.012%" status="up" />
      </div>

      {/* System Load */}
      <div style={{ padding: '0 2px' }}>
        <div className="sec-title">system load</div>
        <MiniBar label="NEURAL ENGINE"  value={78} />
        <MiniBar label="INTENT ROUTER"  value={45} />
        <MiniBar label="MEMORY CACHE"   value={62} />
      </div>

    </div>
  )
}
