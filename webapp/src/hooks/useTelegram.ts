import { useEffect } from 'react'

export function useTelegram() {
  const tg = window.Telegram?.WebApp

  useEffect(() => {
    if (!tg) return
    tg.ready()
    tg.expand()
    tg.BackButton.show()
    const onBack = () => tg.close()
    tg.BackButton.onClick(onBack)
    return () => {
      tg.BackButton.offClick(onBack)
      tg.BackButton.hide()
    }
  }, [tg])

  return {
    user: tg?.initDataUnsafe?.user,
    colorScheme: tg?.colorScheme ?? 'light',
    haptic: tg?.HapticFeedback,
    openLink: (url: string) => tg?.openLink(url),
    themeParams: tg?.themeParams ?? {},
  }
}
