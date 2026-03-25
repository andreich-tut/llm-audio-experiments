import { settingsApi } from '../api/settings'
import { useSettings } from '../hooks/useSettings'
import { useTelegram } from '../hooks/useTelegram'
import type { SettingKey } from '../types'
import OAuthButton from './OAuthButton'
import Section from './Section'
import SettingField from './SettingField'

export default function SettingsPage() {
  const { data, isLoading, error, update, remove, resetSection, refetch } = useSettings()
  const { haptic } = useTelegram()

  const withHaptic =
    <T,>(fn: () => Promise<T>) =>
    async () => {
      haptic?.impactOccurred('light')
      await fn()
    }

  if (isLoading) return <div className="loading">Loading settings…</div>
  if (error) return <div className="error">Failed to load settings</div>
  if (!data) return null

  const { settings, oauth } = data
  const yandex = oauth['yandex'] ?? { connected: false, login: null }

  const field = (label: string, key: SettingKey, secret?: boolean) => (
    <SettingField
      label={label}
      settingKey={key}
      value={settings[key] ?? null}
      secret={secret}
      onSave={async (k, v) => {
        haptic?.impactOccurred('light')
        await update(k, v)
      }}
      onDelete={async (k) => {
        haptic?.impactOccurred('medium')
        await remove(k)
      }}
    />
  )

  return (
    <div className="settings-page">
      <Section title="LLM API" onReset={withHaptic(() => resetSection('llm'))}>
        {field('API Key', 'llm_api_key', true)}
        {field('Base URL', 'llm_base_url')}
        {field('Model', 'llm_model')}
      </Section>

      <Section title="Yandex.Disk" onReset={withHaptic(() => resetSection('yadisk'))}>
        <OAuthButton
          connected={yandex.connected}
          login={yandex.login}
          onDisconnect={() => settingsApi.disconnectYandex().then(refetch)}
          onRefresh={refetch}
        />
        {field('Disk Path', 'yadisk_path')}
      </Section>

      <Section title="Obsidian" onReset={withHaptic(() => resetSection('obsidian'))}>
        {field('Vault Path', 'obsidian_vault_path')}
        {field('Inbox Folder', 'obsidian_inbox_folder')}
      </Section>
    </div>
  )
}
