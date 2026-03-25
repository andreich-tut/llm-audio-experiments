import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SettingsPage from './components/SettingsPage'
import './theme.css'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1 } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <SettingsPage />
    </QueryClientProvider>
  )
}
