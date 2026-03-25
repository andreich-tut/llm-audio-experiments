import { useState } from 'react'
import type { SettingKey } from '../types'

interface SettingFieldProps {
  label: string
  settingKey: SettingKey
  value: string | null
  secret?: boolean
  onSave: (key: SettingKey, value: string) => Promise<void>
  onDelete: (key: SettingKey) => Promise<void>
}

export default function SettingField({
  label,
  settingKey,
  value,
  secret,
  onSave,
  onDelete,
}: SettingFieldProps) {
  const [editing, setEditing] = useState(false)
  const [inputVal, setInputVal] = useState('')
  const [saving, setSaving] = useState(false)

  const isSet = value !== null && value !== undefined

  const handleEdit = () => {
    setInputVal('')
    setEditing(true)
  }

  const handleSave = async () => {
    if (!inputVal.trim()) return
    setSaving(true)
    try {
      await onSave(settingKey, inputVal.trim())
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setSaving(true)
    try {
      await onDelete(settingKey)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setEditing(false)
    setInputVal('')
  }

  const displayValue = () => {
    if (!isSet) return <span className="field-hint">Not set</span>
    if (secret) return <span className="field-secret">••••••••</span>
    return <span className="field-value-text">{value}</span>
  }

  return (
    <div className="setting-field">
      <span className="field-label">{label}</span>

      {editing ? (
        <>
          <input
            className="field-input"
            type={secret ? 'password' : 'text'}
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSave()
              if (e.key === 'Escape') handleCancel()
            }}
            placeholder={secret ? 'Enter new value' : 'Enter value'}
            autoFocus
          />
          <button className="btn btn-primary" onClick={handleSave} disabled={saving || !inputVal.trim()}>
            {saving ? '...' : 'Save'}
          </button>
          <button className="btn btn-ghost" onClick={handleCancel} disabled={saving}>
            Cancel
          </button>
        </>
      ) : (
        <>
          {displayValue()}
          <div className="field-actions">
            <button className="btn btn-ghost" onClick={handleEdit} disabled={saving}>
              {isSet ? 'Edit' : 'Set'}
            </button>
            {isSet && (
              <button className="btn btn-danger" onClick={handleDelete} disabled={saving}>
                {saving ? '...' : 'Clear'}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}
