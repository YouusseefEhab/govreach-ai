import { queryOptions, QueryClient } from '@tanstack/react-query'
import { checkBackend, listCampaigns } from './services/api'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, staleTime: 30_000, refetchOnWindowFocus: false },
    mutations: { retry: false },
  },
})

export const healthQuery = queryOptions({
  queryKey: ['health'],
  queryFn: ({ signal }) => checkBackend(signal),
})

export const campaignsQuery = (skip: number, limit: number) => queryOptions({
  queryKey: ['campaigns', { skip, limit }],
  queryFn: ({ signal }) => listCampaigns(skip, limit, signal),
})
