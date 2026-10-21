import assert from 'node:assert/strict'
import { after, afterEach, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createServer } from 'vite'

let server: Awaited<ReturnType<typeof createServer>>
let App: () => ReturnType<typeof createElement>
let renderConfirmation: (busy: boolean) => string
let renderGeneration: (busy: boolean, disabled?: boolean) => string
let renderContent: (language?: 'arabic' | 'english') => string
let setUiLanguage: (language: 'ar' | 'en') => void
let renderReview: (dirty: boolean, busy: boolean, status?: string) => string

before(async () => {
  server = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  App = (await server.ssrLoadModule('/src/App.tsx')).default
  setUiLanguage = (await server.ssrLoadModule('/src/i18n.ts')).setInterfaceLanguage
  const { DeleteConfirmation } = await server.ssrLoadModule('/src/components/DeleteCampaign.tsx')
  renderConfirmation = (busy) => renderToStaticMarkup(createElement(DeleteConfirmation, {
    title: '<script>unsafe</script>', busy, confirm: () => {}, cancel: () => {},
  }))
  const { GenerationForm } = await server.ssrLoadModule('/src/components/GenerationWorkspace.tsx')
  renderGeneration = (busy, disabled = false) => renderToStaticMarkup(createElement(GenerationForm, {
    busy, disabled, submit: async () => { throw new Error('Rendering must never submit') },
  }))
  const { default: ContentCard } = await server.ssrLoadModule('/src/components/ContentCard.tsx')
  renderContent = (language = 'english') => renderToStaticMarkup(createElement(ContentCard, { showEditorLink: false, item: {
    id: 15, campaign_id: 27, generation_id: 'f23507de-84ac-46a6-9f07-a44918edf4b2', language,
    review_status: 'draft', provider: 'fake', model: 'test', prompt_version: 'test', created_at: '2026-10-21T12:00:00Z',
    source_references: [{ title: '<script>unsafe</script>', url: 'javascript:alert(1)' }],
    content: { headline: '<script>text</script>', slogan: 'حزامك أمانك', awareness_message: 'Message', social_caption: 'Caption', call_to_action: 'Action' },
  } }))
  const { ReviewActions } = await server.ssrLoadModule('/src/pages/ContentEditor.tsx')
  renderReview = (dirty, busy, status = 'draft') => renderToStaticMarkup(createElement(ReviewActions, {
    dirty, busy, status, review: () => { throw new Error('Rendering must not review content') },
  }))
})
after(async () => { await server?.close() })
afterEach(() => { setUiLanguage?.('ar') })

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

test('review controls require saved content and remain disabled while saving', () => {
  for (const [dirty, busy] of [[true, false], [false, true]]) {
    assert.equal((renderReview(dirty, busy).match(/disabled=""/g) ?? []).length, 2)
  }
  assert.ok(renderReview(true, false).includes('احفظ التعديلات الأول'))
  assert.equal((renderReview(false, false).match(/disabled=""/g) ?? []).length, 0)
  assert.equal((renderReview(false, false, 'approved').match(/disabled=""/g) ?? []).length, 1)
})

test('content editor reload route shows stored fields, status and source context', () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(['health'], { status: 'healthy' })
  client.setQueryData(['content', 15], {
    id: 15, campaign_id: 27, generation_id: 'f23507de-84ac-46a6-9f07-a44918edf4b2', language: 'english',
    review_status: 'approved', content_type: 'text_package', provider: 'fake', model: 'test', prompt_version: 'test',
    created_at: '2026-10-21T12:00:00Z', input_snapshot: {}, source_references: [],
    content: { headline: 'Saved headline', slogan: 'Saved slogan', awareness_message: 'Saved message', social_caption: 'Caption', call_to_action: 'Action' },
  })
  const router = createMemoryRouter([{ path: '*', element: createElement(App) }], { initialEntries: ['/contents/15'] })
  try {
    const html = renderToStaticMarkup(createElement(QueryClientProvider, { client }, createElement(RouterProvider, { router })))
    assert.ok(html.includes('Saved headline'))
    assert.ok(html.includes('lang="en" dir="ltr"'))
    assert.ok(html.includes('معتمد'))
    assert.ok(html.includes('آخر نسخة محفوظة'))
    assert.ok(html.includes('بيرجّع النسخة لمسودة'))
  } finally { router.dispose(); client.clear() }
})

test('English screens translate navigation and forms without translating campaign data', () => {
  setUiLanguage('en')
  const home = render('/')
  assert.ok(home.includes('Campaign workspace'))
  assert.ok(home.includes('Server connected'))
  assert.ok(home.includes('for="interface-language"'))
  const form = render('/campaigns/new')
  assert.ok(form.includes('Campaign title'))
  assert.ok(form.includes('Save campaign'))
  assert.ok(form.includes('value="both" selected=""'))
  const list = render('/campaigns', [{ id: 27, title: 'رسالة عربية', objective: 'Keep content', domain: 'traffic_safety', language: 'both', status: 'draft', created_at: '2026-10-21T12:00:00Z' }])
  assert.ok(list.includes('<bdi>رسالة عربية</bdi>'))
  assert.ok(list.includes('Arabic and English'))
  assert.ok(list.includes('Draft'))
})

test('English interface preserves Arabic package direction and adds exact-text copy controls', () => {
  setUiLanguage('en')
  const html = renderContent('arabic')
  assert.ok(html.includes('lang="ar-EG" dir="rtl"'))
  assert.ok(html.includes('حزامك أمانك'))
  assert.ok(html.includes('Copy all text'))
  assert.ok(html.includes('Copy Slogan'))
  assert.ok(html.includes('Draft for review'))
  assert.ok(html.includes('Sources and generation details'))
})
