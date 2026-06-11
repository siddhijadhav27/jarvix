'use client'
import { useClock } from '@/hooks/useClock'

export default function Header() {
  const time = useClock()

  return (
    <header className="jv-header">
      <div className="header-brand">
        JARVIX · AI-POWERED CRYPTO COMMAND CENTER · v2.0
      </div>

      <div className="header-clock">{time}</div>

      <div className="header-status">
        <div className="hstat">
          <div className="hstat-dot" />
          KIMI ONLINE
        </div>
        <div className="hstat">
          <div className="hstat-dot online" />
          3 ONLINE
        </div>
        <div className="hstat" style={{ color: 'var(--c3)' }}>
          SYS · NOMINAL
        </div>
      </div>
    </header>
  )
}
