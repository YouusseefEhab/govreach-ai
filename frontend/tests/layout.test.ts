import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createServer } from 'vite'

let server: Awaited<ReturnType<typeof createServer>>
let App: () => ReturnType<typeof createElement>

before(async () => {
  server = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  App = (await server.ssrLoadModule('/src/App.tsx')).default
})
after(async () => { await server?.close() })

function render(path: string, records?: unknown[], campaign?: unknown) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(['health'], { status: 'healthy' })
  if (records) {
    client.setQueryData(['campaigns', { skip: 0, limit: 20 }], records)
  }
  if (campaign) client.setQueryData(['campaign', 27], campaign)
  try {
    return renderToStaticMarkup(createElement(QueryClientProvider, { client },
      createElement(MemoryRouter, { initialEntries: [path] }, createElement(App))))
  } finally {
    client.clear()
  }
}

test('home shows Arabic navigation, live health contract, and a campaign link', () => {
  const html = render('/')
  assert.ok(html.includes('السيرفر متصل'))
  assert.ok(html.includes('كل حملة بتبدأ'))
  assert.ok(html.includes('href="/campaigns"'))
  assert.ok(!html.includes('Campaign creation will be implemented next'))
})

test('campaign list preserves mixed-language titles and disables unavailable pages', () => {
  const html = render('/campaigns', [{
    id: 7, title: 'حزام الأمان / Seat belts', objective: 'Test',
    domain: 'traffic_safety', language: 'both', status: 'draft',
    created_at: '2026-10-13T17:59:49Z',
  }])
  assert.ok(html.includes('<bdi>حزام الأمان / Seat belts</bdi>'))
  assert.ok(html.includes('عربي وإنجليزي'))
  assert.equal((html.match(/disabled=""/g) ?? []).length, 2)
})

test('empty campaigns show an honest empty state without fabricated totals', () => {
  const html = render('/campaigns', [])
  assert.ok(html.includes('لسه مفيش حملات محفوظة'))
  assert.ok(!html.includes('<table'))
})

test('unknown routes offer a working recovery link', () => {
  const html = render('/does-not-exist')
  assert.ok(html.includes('الصفحة مش موجودة'))
  assert.ok(html.includes('href="/campaigns"'))
})

test('new campaign route provides labelled Arabic fields and separate saving action', () => {
  const html = render('/campaigns/new')
  assert.ok(html.includes('for="title"'))
  assert.ok(html.includes('for="objective"'))
  assert.ok(html.includes('for="language"'))
  assert.ok(html.includes('احفظ الحملة'))
  assert.ok(html.includes('value="both" selected=""'))
  assert.ok(!html.includes('الصفحة مش موجودة'))
})

test('saved campaign detail displays its original brief and selected language', () => {
  const html = render('/campaigns/27', undefined, {
    id: 27, title: 'Seat belt safety', objective: 'هدف الحملة\nرسالة تانية',
    domain: 'traffic_safety', language: 'english', status: 'draft', created_at: '2026-10-21T12:00:00Z',
  })
  assert.ok(html.includes('dir="auto">Seat belt safety'))
  assert.ok(html.includes('هدف الحملة\nرسالة تانية'))
  assert.ok(html.includes('إنجليزي'))
})

test('invalid campaign IDs offer recovery rather than starting a query', () => {
  assert.ok(render('/campaigns/not-an-id').includes('رقم الحملة غير صحيح'))
})
