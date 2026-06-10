'use client'
import { useState, useRef } from 'react'
import { arcFlash } from '@/utils/animations'

interface CommandInterfaceProps {
  onCommand?: (cmd: string, result: string) => void
  sendCommand?: (cmd: string) => Promise<any>
  sending?: boolean
}

export default function CommandInterface({
  onCommand,
  sendCommand,
  sending = false,
}: CommandInterfaceProps) {
  const [input, setInput] = useState('')
  const [response, setResponse] = useState(
    <>An enthusiastic yet remarkably incomplete command, sir. Portfolio flourishing at{' '}
      <em>$311,342</em>, up <em>2.4%</em>. Holdings: <em>0.5 BTC</em>, <em>100 ETH</em>,{' '}
      <em>500 SOL</em>. Might I inquire — <em>buy what, precisely?</em></>
  )
  const inputRef = useRef<HTMLInputElement>(null)

  const transmit = async () => {
    if (!input.trim() || sending) return
    const cmd = input.trim()

    // Flash arc reactor
    arcFlash()

    // Show processing state
    setResponse(<>Processing: <em>{cmd.toUpperCase()}</em> — analyzing intent, sir. Stand by.</>)

    if (sendCommand) {
      const result = await sendCommand(cmd)
      if (result) {
        setResponse(
          <>
            Intent: <em>{result.intent}</em> · Confidence: <em>{result.confidence}</em>
            <br />
            {result.message || result.response || 'No response from AI, sir.'}
          </>
        )
        onCommand?.(cmd, result.message)
      }
    }

    setInput('')
  }

  return (
    <div>
      <div className="sec-title" style={{ marginBottom: '10px' }}>command interface</div>

      <div className="cmd-wrap">
        <span className="cmd-prefix">&gt;</span>
        <input
          ref={inputRef}
          className="cmd-in"
          type="text"
          placeholder="enter command, sir..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && transmit()}
          disabled={sending}
        />
        <button className="cmd-btn" onClick={transmit} disabled={sending}>
          {sending ? 'PROCESSING' : 'TRANSMIT'}
        </button>
      </div>

      <div style={{ marginTop: '14px' }}>
        <div className="res-msg">{response}</div>
      </div>
    </div>
  )
}
