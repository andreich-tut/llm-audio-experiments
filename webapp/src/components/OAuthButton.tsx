import { useEffect, useState } from 'react'
import { settingsApi } from '../api/settings'

interface OAuthButtonProps {
  connected: boolean
  login: string | null
  onDisconnect: () => Promise<void>
  onRefresh: () => void
}

export default function OAuthButton({ connected, login, onDisconnect, onRefresh }: OAuthButtonProps) {
  const [loading, setLoading] = useState(false)

  // Re-fetch settings when user returns to the Mini App after OAuth flow
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        onRefresh()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [onRefresh])

  const handleConnect = async () => {
    setLoading(true)
    try {
      const { url } = await settingsApi.getYandexOAuthUrl()
      window.Telegram?.WebApp?.openLink(url)
    } finally {
      setLoading(false)
    }
  }

  const handleDisconnect = async () => {
    setLoading(true)
    try {
      await onDisconnect()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="oauth-row">
      {connected ? (
        <>
          <span className="field-value-text">
            {login ? `Connected: ${login}` : 'Connected'}
          </span>
          <button className="btn btn-danger" onClick={handleDisconnect} disabled={loading}>
            {loading ? '...' : 'Disconnect'}
          </button>
        </>
      ) : (
        <button className="btn btn-primary" onClick={handleConnect} disabled={loading}>
          {loading ? 'Opening...' : 'Connect Yandex.Disk'}
        </button>
      )}
    </div>
  )
}
