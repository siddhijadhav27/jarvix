import { useState, useEffect, useCallback, useRef } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
const WS_BASE  = process.env.NEXT_PUBLIC_WS_URL  || 'ws://localhost:8001'

// ── Types ──────────────────────────────
export interface IntentResult {
  intent: string
  confidence: number
  fast_path: boolean
  source: string
  entities: { asset: string | null; amount: string | null; price: string | null }
  message: string
  latency_ms: number
}

export interface PortfolioData {
  total_value: number
  change_pct: number
  holdings: { asset: string; amount: number; value: number }[]
}

export interface SystemHealth {
  neural_engine: number
  intent_router: number
  memory_cache: number
  commands_total: number
  pass_rate: number
  redis_status: string
  learning_db: string
}

export interface LivePrices {
  BTC: number
  ETH: number
  SOL: number
}

// ── Main Hook ──────────────────────────
export function useJarvixAPI() {
  const [portfolio, setPortfolio]   = useState<PortfolioData | null>(null)
  const [health, setHealth]         = useState<SystemHealth | null>(null)
  const [prices, setPrices]         = useState<LivePrices | null>(null)
  const [lastIntent, setLastIntent] = useState<IntentResult | null>(null)
  const [sending, setSending]       = useState(false)

  const wsRef = useRef<WebSocket | null>(null)

  // ── Fetch portfolio ──
  const fetchPortfolio = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/portfolio`)
      if (res.ok) setPortfolio(await res.json())
    } catch { /* backend not running — use demo data */ }
  }, [])

  // ── Fetch system health ──
  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`)
      if (res.ok) setHealth(await res.json())
    } catch { /* backend not running */ }
  }, [])

  // ── Send command to Jarvix ──
  const sendCommand = useCallback(async (command: string): Promise<IntentResult | null> => {
    setSending(true)
    try {
      const res = await fetch(`${API_BASE}/api/ai/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: command, user_id: 'siddhi' }),
      })
      if (res.ok) {
        const data = await res.json()
        setLastIntent(data)
        return data
      }
    } catch {
      // Demo fallback when backend offline
      const demo: IntentResult = {
        intent: 'UNKNOWN',
        confidence: 0,
        fast_path: false,
        source: 'offline',
        entities: { asset: null, amount: null, price: null },
        message: 'Backend offline — running in demo mode, sir.',
        latency_ms: 0,
      }
      setLastIntent(demo)
      return demo
    } finally {
      setSending(false)
    }
    return null
  }, [])

  // ── WebSocket for live prices ──
  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(`${WS_BASE}/ws/prices`)
        wsRef.current = ws

        ws.onmessage = (e) => {
          try { setPrices(JSON.parse(e.data)) } catch { /* ignore */ }
        }
        ws.onclose = () => {
          // Reconnect after 3s
          setTimeout(connect, 3000)
        }
        ws.onerror = () => ws.close()
      } catch { /* WebSocket not available */ }
    }

    connect()
    return () => wsRef.current?.close()
  }, [])

  // ── Initial fetches ──
  useEffect(() => {
    fetchPortfolio()
    fetchHealth()
    const id = setInterval(() => {
      fetchPortfolio()
      fetchHealth()
    }, 30000) // refresh every 30s
    return () => clearInterval(id)
  }, [fetchPortfolio, fetchHealth])

  return { portfolio, health, prices, lastIntent, sending, sendCommand }
}
