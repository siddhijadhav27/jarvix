'use client'

interface ModelProps {
  name: string
  type: 'cloud' | 'local'
  latency?: string
  status: 'on' | 'off' | 'dl'
}

function ModelRow({ name, type, latency, status }: ModelProps) {
  const statusLabel = status === 'on' ? 'ACTIVE' : status === 'dl' ? 'INIT' : 'OFFLINE'
  return (
    <div className="model-item">
      <div className={`mdot ${status}`} />
      <div className="mname">{name}</div>
      <div className="model-type" style={{
        fontFamily: 'var(--font-m)', fontSize: '0.58rem', color: 'var(--c3)'
      }}>
        {type.toUpperCase()}
      </div>
      <div className="latency" style={{
        fontFamily: 'var(--font-m)', fontSize: '0.62rem', color: 'var(--c3)'
      }}>
        {latency ?? '—'}
      </div>
      <div className={`mstatus ${status}`}>{statusLabel}</div>
    </div>
  )
}

interface ModelStatusProps {
  activeModel?: string
}

export default function ModelStatus({ activeModel = 'KIMI VIA HERMES' }: ModelStatusProps) {
  return (
    <div className="bracket" style={{ padding: '12px' }}>
      <div className="sec-title">neural router</div>

      <ModelRow name="Kimi via Hermes" type="cloud" latency="~8000ms" status="on" />
      <ModelRow name="Qwen 2.5 (Local)" type="local" status="dl" />
      <ModelRow name="Llama 3.2 (Local)" type="local" status="dl" />

      <div style={{
        marginTop: '12px', fontFamily: 'var(--font-m)',
        fontSize: '0.58rem', color: 'var(--c3)', letterSpacing: '0.12em',
        lineHeight: '1.8'
      }}>
        ACTIVE &nbsp;·&nbsp;{' '}
        <span style={{ color: 'var(--c)' }}>{activeModel}</span>
        <br />
        <span style={{ color: 'var(--c4)' }}>cloud · hermes bridge</span>
      </div>
    </div>
  )
}
