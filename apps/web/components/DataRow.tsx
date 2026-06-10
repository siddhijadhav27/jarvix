'use client'

interface DataRowProps {
  label: string
  value: string | number
  status?: 'up' | 'down' | 'warn' | 'default'
  small?: boolean
}

export default function DataRow({ label, value, status = 'default', small }: DataRowProps) {
  const valClass = `drow-val${status !== 'default' ? ` ${status}` : ''}`
  return (
    <div className="drow">
      <span className="drow-key" style={small ? { fontSize: '0.58rem' } : {}}>{label}</span>
      <span className={valClass} style={small ? { fontSize: '0.6rem' } : {}}>{value}</span>
    </div>
  )
}
