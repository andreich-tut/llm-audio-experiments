export interface OAuthStatus {
  connected: boolean
  login: string | null
}

export interface SettingsResponse {
  settings: Record<string, string | null>
  oauth: Record<string, OAuthStatus>
}

export type SettingKey =
  | 'llm_api_key'
  | 'llm_base_url'
  | 'llm_model'
  | 'yadisk_path'
  | 'obsidian_vault_path'
  | 'obsidian_inbox_folder'

export type SectionId = 'llm' | 'yadisk' | 'obsidian'
