'use client'
import ModelStatus from './ModelStatus'
import DataRow from './DataRow'

interface RightPanelProps {
  lastIntent?: {
    command?: string
    intent?: string
    confidence?: number
    fastPath?: boolean
    source?: string
    latency?: number
  }
}

export default function RightPanel({ lastIntent }: RightPanelProps) {
  const li = lastIntent ?? {
    command: 'BUY',
    intent: 'BUY',
    confidence: 0.95,
    fastPath: false,
    source: 'LLM',
    latency: 29036,
  }

  return (
    <div className="right-panel">

      {/* Neural Router */}
      <ModelStatus />

      {/* Last Intent */}
      <div className="bracket" style={{ padding: '12px' }}>
        <div className="sec-title">last intent</div>
        <DataRow label="COMMAND"    value={li.command ?? '—'} />
        <DataRow label="INTENT"     value={li.intent ?? '—'} status="up" />
        <DataRow label="CONFIDENCE" value={String(li.confidence ?? '—')} />
        <DataRow label="FAST PATH"  value={li.fastPath ? 'TRUE' : 'FALSE'} status={li.fastPath ? 'up' : 'warn'} />
        <DataRow label="SOURCE"     value={li.source ?? '—'} />
        <DataRow label="LATENCY"    value={`${li.latency ?? 0}ms`} status={li.latency && li.latency > 5000 ? 'warn' : 'default'} />
      </div>

      {/* Holdings */}
      <div className="bracket" style={{ padding: '12px' }}>
        <div className="sec-title">holdings</div>
        <DataRow label="BTC" value="0.5  ≈ $36,542" />
        <DataRow label="ETH" value="100  ≈ $199,795" />
        <DataRow label="SOL" value="500  ≈ $76,200" />
      </div>

    </div>
  )
}
