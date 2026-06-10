'use client'
import { useEffect, useRef } from 'react'

interface DiagProps {
  name: string
  pct?: number
  pass: boolean
  time: string
  delay?: number
}

export default function DiagnosticBar({ name, pct = 100, pass, time, delay = 0 }: DiagProps) {
  const fillRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const t = setTimeout(() => {
      if (fillRef.current) fillRef.current.style.width = pct + '%'
    }, 700 + delay)
    return () => clearTimeout(t)
  }, [pct, delay])

  return (
    <div className="diag" style={{ animationDelay: `${delay / 1000}s` }}>
      <div className="diag-n">{name}</div>
      <div className="diag-bar">
        <div className="diag-fill" ref={fillRef} style={{ width: '0%' }} />
      </div>
      <div className={`diag-s ${pass ? 'p' : 'f'}`}>{pass ? 'PASS' : 'FAIL'}</div>
      <div className="diag-t">{time}</div>
    </div>
  )
}
