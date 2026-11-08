import assert from 'node:assert/strict'
import { after, afterEach, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createServer } from 'vite'

let server: Awaited<ReturnType<typeof createServer>>
let ImageCard: (props: object) => ReturnType<typeof createElement>
let ImageWorkspace: (props: object) => ReturnType<typeof createElement>
let ImageBriefForm: (props: object) => ReturnType<typeof createElement>
let setLanguage: (lang: 'ar' | 'en') => void
let saveAttempt: (attempt: object) => boolean
let clearAttempt: (id: number) => void
const date = '2026-11-08T12:00:00Z'
const brief = { source_content_id: 15, visual_brief: 'A parked car', style: 'illustration' }
const campaign = { id: 27, title: 'Test campaign', objective: 'Safety', domain: 'traffic_safety', language: 'both', status: 'draft', created_at: date }
const image = {
  id: 51, campaign_id: 27, source_content_id: 15, idempotency_key: 'image_test_1', request_state: 'ready', review_status: 'draft', source_is_current: true,
  source_snapshot: { language: 'arabic', content: { headline: '<script>unsafe</script>' } }, source_references: [],
  visual_brief: 'Safe scene <script>unsafe</script>', style: 'illustration', provider: 'fake', model: 'fake-image-v1', prompt_version: 'traffic-image-v1',
  mime_type: 'image/png', width: 32, height: 32, byte_count: 99, failure_code: null, created_at: date, updated_at: date,
}

before(async () => {
  server = await createServer({ cacheDir: 'node_modules/.vite-image-tests', server: { middlewareMode: true, ws: false }, appType: 'custom' })
  ImageCard = (await server.ssrLoadModule('/src/components/ImageCard.tsx')).default
  const workspace = await server.ssrLoadModule('/src/components/ImageWorkspace.tsx')
  ImageWorkspace = workspace.default
  ImageBriefForm = workspace.ImageBriefForm
  setLanguage = (await server.ssrLoadModule('/src/i18n.ts')).setInterfaceLanguage
  const images = await server.ssrLoadModule('/src/services/images.ts')
  saveAttempt = images.saveImageAttempt
  clearAttempt = images.clearImageAttempt
})
after(async () => { await server?.close() })
afterEach(() => { setLanguage('ar'); clearAttempt(27) })

function render(component: typeof ImageCard, props: object, setup?: (client: QueryClient) => void) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  setup?.(client)
  try {
    return renderToStaticMarkup(createElement(QueryClientProvider, { client }, createElement(MemoryRouter, null,
      createElement(component, props))))
  } finally { client.clear() }
}

test('image card escapes source/brief text and has controlled preview and download links', () => {
  const html = render(ImageCard, { item: image })
  assert.ok(html.includes('/api/v1/images/51/file'))
  assert.ok(html.includes('/api/v1/images/51/file?download=true'))
  assert.ok(html.includes('صورة اختبار زرقا'))
  assert.ok(html.includes('مراجعة الصورة بشكل مستقل'))
  assert.ok(!html.includes('<script>'))
  assert.ok(html.includes('&lt;script&gt;'))
  // Loading a preview alone is not human review; approval starts disabled.
  assert.match(html, /<button[^>]*disabled=""[^>]*>اعتماد الصورة<\/button>/)
})

test('non-ready image states have no image file, download or review controls', () => {
  for (const state of ['reserved', 'generating', 'failed', 'outcome_unknown']) {
    const html = render(ImageCard, { item: { ...image, request_state: state, width: null, height: null, mime_type: null, byte_count: null } })
    assert.ok(!html.includes('<img'))
    assert.ok(!html.includes('download=true'))
    assert.ok(!html.includes('>اعتماد الصورة</button>'))
    assert.ok(html.includes('مفيش ملف جاهز'))
  }
})

test('snapshot text keeps its language direction and only HTTPS source links are clickable', () => {
  const html = render(ImageCard, { item: { ...image, source_snapshot: { language: 'arabic', content: { headline: 'حزامك أمانك' } },
    source_references: [{ title: 'Unsafe', url: 'javascript:alert(1)' }, { title: 'WHO', url: 'https://www.who.int/' }] } })
  assert.ok(html.includes('dir="rtl" lang="ar-EG"'))
  assert.ok(html.includes('حزامك أمانك'))
  assert.ok(!html.includes('href="javascript:'))
  assert.ok(html.includes('href="https://www.who.int/"'))
})

test('stale approved images display historical approval and block another approval', () => {
  const html = render(ImageCard, { item: { ...image, review_status: 'approved', source_is_current: false } })
  assert.ok(html.includes('الاعتماد الظاهر قرار سابق'))
  assert.match(html, /<button[^>]*disabled=""[^>]*>اعتماد الصورة<\/button>/)
  assert.ok(html.includes('download=true'))
})

test('brief form requires source selection and disables all fields while pending', () => {
  const submit = async () => { throw new Error('Rendering must not generate') }
  for (const state of [{ sourceId: 0, busy: false, disabled: true }, { sourceId: 15, busy: true, disabled: false }]) {
    const html = render(ImageBriefForm, { ...state, submit })
    assert.ok(html.includes('<fieldset disabled="">'))
    assert.ok(html.includes('for="image-brief"'))
    assert.ok(html.includes('for="image-style"'))
    assert.ok(!html.includes('type="submit" on'))
  }
})

function source(id: number, status: string) {
  return { id, campaign_id: 27, language: 'arabic', review_status: status,
    content: { headline: status === 'approved' ? 'Approved headline' : 'Unreviewed headline' } }
}

test('source choices show only approved packages and empty image history is honest', () => {
  const html = render(ImageWorkspace, { campaign }, (client) => {
    client.setQueryData(['campaign-contents', 27, { skip: 0, limit: 20 }], [source(15, 'approved'), source(16, 'draft')])
    client.setQueryData(['campaign-images', 27, { skip: 0, limit: 20 }], [])
  })
  assert.ok(html.includes('Approved headline'))
  assert.ok(!html.includes('Unreviewed headline'))
  assert.ok(html.includes('مفيش صور محفوظة'))
  assert.ok(html.includes('صفحات النصوص لاختيار الصورة'))
  assert.ok(html.includes('صفحات الصور'))
})

test('restored attempt preserves its key, explains uncertainty and requires acknowledgement for a new request', () => {
  saveAttempt({ campaign_id: 27, key: 'recover_original_key', request: brief })
  const html = render(ImageWorkspace, { campaign }, (client) => {
    client.setQueryData(['campaign-contents', 27, { skip: 0, limit: 20 }], [])
    client.setQueryData(['campaign-images', 27, { skip: 0, limit: 20 }], [{ ...image, idempotency_key: 'recover_original_key', request_state: 'outcome_unknown' }])
  })
  assert.ok(html.includes('recover_original_key'))
  assert.ok(html.includes('نتيجة الطلب غير مؤكدة'))
  assert.ok(html.includes('استرجاع أو استكمال نفس الطلب'))
  assert.match(html, /<button[^>]*disabled=""[^>]*>تجهيز طلب صورة جديد<\/button>/)
  assert.ok(!html.includes('id="image-brief"'))
})

test('image history and review are translated without translating stored scene descriptions', () => {
  setLanguage('en')
  const html = render(ImageCard, { item: { ...image, visual_brief: 'مشهد عربي محفوظ' } })
  assert.ok(html.includes('Download image'))
  assert.ok(html.includes('Independent image review'))
  assert.ok(html.includes('مشهد عربي محفوظ'))
  assert.ok(html.includes('Image ready'))
})
