import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createServer } from 'vite'

let server: Awaited<ReturnType<typeof createServer>>
let App: () => ReturnType<typeof createElement>
let renderConfirmation: (busy: boolean) => string
let renderGeneration: (busy: boolean, disabled?: boolean) => string
let renderContent: () => string

before(async () => {
  server = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  App = (await server.ssrLoadModule('/src/App.tsx')).default
  const { DeleteConfirmation } = await server.ssrLoadModule('/src/components/DeleteCampaign.tsx')
  renderConfirmation = (busy) => renderToStaticMarkup(createElement(DeleteConfirmation, {
    title: '<script>unsafe</script>', busy, confirm: () => {}, cancel: () => {},
  }))
  const { GenerationForm } = await server.ssrLoadModule('/src/components/GenerationWorkspace.tsx')
  renderGeneration = (busy, disabled = false) => renderToStaticMarkup(createElement(GenerationForm, {
    busy, disabled, submit: async () => { throw new Error('Rendering must never submit') },
  }))
  const { default: ContentCard } = await server.ssrLoadModule('/src/components/ContentCard.tsx')
  renderContent = () => renderToStaticMarkup(createElement(ContentCard, { item: {
    id: 15, campaign_id: 27, generation_id: 'f23507de-84ac-46a6-9f07-a44918edf4b2', language: 'english',
    review_status: 'draft', provider: 'fake', model: 'test', prompt_version: 'test', created_at: '2026-10-21T12:00:00Z',
    source_references: [{ title: '<script>unsafe</script>', url: 'javascript:alert(1)' }],
    content: { headline: '<script>text</script>', slogan: 'Slogan', awareness_message: 'Message', social_caption: 'Caption', call_to_action: 'Action' },
  } }))
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

test('edit route prefills the saved campaign and explains history preservation', () => {
  const html = render('/campaigns/27/edit', undefined, {
    id: 27, title: 'Existing title', objective: 'Existing objective', domain: 'custom_domain',
    language: 'english', status: 'draft', created_at: '2026-10-21T12:00:00Z',
  })
  assert.ok(html.includes('value="Existing title"'))
  assert.ok(html.includes('Existing objective'))
  assert.ok(html.includes('value="english" selected=""'))
  assert.ok(html.includes('المسودات القديمة'))
  assert.ok(html.includes('custom_domain'))
  assert.ok(html.includes('احفظ التعديلات'))
})

test('delete confirmation names the cascade, escapes titles, and blocks actions while pending', () => {
  const idle = renderConfirmation(false)
  assert.ok(idle.includes('كل المحتوى المتولّد وسجل التوليد'))
  assert.ok(idle.includes('إلغاء الحذف'))
  assert.ok(idle.includes('أيوه، احذف الحملة ومحتواها'))
  assert.ok(!idle.includes('<script>'))
  const pending = renderConfirmation(true)
  assert.equal((pending.match(/disabled=""/g) ?? []).length, 2)
  assert.ok(pending.includes('بنحذف الحملة…'))
})

test('generation render never submits and pending/recovery states disable the form', () => {
  assert.ok(renderGeneration(false).includes('ولّد مسودة جديدة'))
  const pending = renderGeneration(true)
  assert.ok(pending.includes('<fieldset disabled="">'))
  assert.ok(pending.includes('بنجهّز المسودة'))
  assert.ok(pending.includes('الخروج من الصفحة مش بيلغي التوليد'))
  assert.ok(renderGeneration(false, true).includes('<fieldset disabled="">'))
})

test('content uses its own direction and plain text; unsafe source links are not rendered', () => {
  const html = renderContent()
  assert.ok(html.includes('lang="en" dir="ltr"'))
  assert.ok(html.includes('مسودة للمراجعة'))
  assert.ok(html.includes('مش تدقيق تلقائي'))
  assert.ok(!html.includes('<script>'))
  assert.ok(!html.includes('href="javascript:'))
})
