'use client'
import DiagnosticBar from './DiagnosticBar'
import CommandInterface from './CommandInterface'
import DataRow from './DataRow'
import { useUptime } from '@/hooks/useUptime'

interface BottomBarProps {
  sendCommand?: (cmd: string) => Promise<any>
  sending?: boolean
}

export default function BottomBar({ sendCommand, sending }: BottomBarProps) {
  const uptime = useUptime()

  return (
    <div className="jv-bottom">

      {/* Diagnostics */}
      <div className="bottom-left">
        <div className="sec-title" style={{ marginBottom: '10px' }}>diagnostics</div>
        <DiagnosticBar name="INTENT DETECT"  pass={true}  time="0.40s" delay={100}  />
        <DiagnosticBar name="CONFIDENCE"     pass={true}  time="0.80s" delay={250}  />
        <DiagnosticBar name="FAST PATH"      pass={true}  time="1.20s" delay={400}  />
        <DiagnosticBar name="COMPLETENESS"   pass={true}  time="1.60s" delay={550}  />
      </div>

      {/* Command Interface */}
      <div className="bottom-center">
        <CommandInterface sendCommand={sendCommand} sending={sending} />
      </div>

      {/* System Status */}
      <div className="bottom-right">
        <div className="sec-title" style={{ marginBottom: '10px' }}>system status</div>
        <DataRow label="UPTIME"       value={uptime} />
        <DataRow label="COMMANDS"     value="284" />
        <DataRow label="PASS RATE"    value="100%" status="up" />
        <DataRow label="LEARNING DB"  value="ACTIVE" status="up" />
        <DataRow label="REDIS"        value="CONNECTED" status="up" />
        <DataRow label="REPO"         value="siddhijadhav27" small />
      </div>

    </div>
  )
}
