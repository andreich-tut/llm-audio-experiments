import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { settingsApi } from '../api/settings'
import type { SettingKey, SectionId } from '../types'

export function useSettings() {
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ['settings'] })

  const query = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.getAll,
    staleTime: 30_000,
  })

  const update = useMutation({
    mutationFn: ({ key, value }: { key: SettingKey; value: string }) =>
      settingsApi.update(key, value),
    onSuccess: invalidate,
  })

  const remove = useMutation({
    mutationFn: (key: SettingKey) => settingsApi.delete(key),
    onSuccess: invalidate,
  })

  const resetSection = useMutation({
    mutationFn: (section: SectionId) => settingsApi.resetSection(section),
    onSuccess: invalidate,
  })

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    update: (key: SettingKey, value: string) => update.mutateAsync({ key, value }),
    remove: (key: SettingKey) => remove.mutateAsync(key),
    resetSection: (section: SectionId) => resetSection.mutateAsync(section),
    refetch: invalidate,
  }
}
