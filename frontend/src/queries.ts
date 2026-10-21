import { queryOptions, QueryClient } from '@tanstack/react-query'
import { checkBackend, getCampaign, getContent, listCampaigns, listContents } from './services/api'

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

export const campaignQuery = (id: number) => queryOptions({
  queryKey: ['campaign', id],
  queryFn: ({ signal }) => getCampaign(id, signal),
  enabled: Number.isSafeInteger(id) && id > 0,
})

export const contentsQuery = (id: number, skip = 0, limit = 20) => queryOptions({
  queryKey: ['campaign-contents', id, { skip, limit }],
  queryFn: ({ signal }) => listContents(id, skip, limit, signal),
})

export const contentQuery = (id: number) => queryOptions({
  queryKey: ['content', id],
  queryFn: ({ signal }) => getContent(id, signal),
  enabled: Number.isSafeInteger(id) && id > 0,
})
