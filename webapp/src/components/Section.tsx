import { useState } from 'react'

interface SectionProps {
  title: string
  children: React.ReactNode
  onReset?: () => Promise<void>
}

export default function Section({ title, children, onReset }: SectionProps) {
  const [resetting, setResetting] = useState(false)

  const handleReset = async () => {
    if (!onReset) return
    setResetting(true)
    try {
      await onReset()
    } finally {
      setResetting(false)
    }
  }

  return (
    <div className="section">
      <div className="section-header">
        <span>{title}</span>
        {onReset && (
          <button className="btn btn-ghost" onClick={handleReset} disabled={resetting}>
            {resetting ? '...' : 'Reset'}
          </button>
        )}
      </div>
      <div className="section-content">{children}</div>
    </div>
  )
}
