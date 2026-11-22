import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { after, before, test } from 'node:test'
import { setImmediate as turn } from 'node:timers/promises'
import { runInNewContext } from 'node:vm'
import { MutationObserver, QueryClient, QueryClientProvider, QueryObserver } from '@tanstack/react-query'
import { Children, createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import * as jsxRuntime from 'react/jsx-runtime'
import { MemoryRouter } from 'react-router-dom'
import ts from 'typescript'
import { createServer } from 'vite'

let vite
let App
let LanguageProvider
let MarketingGenerationForm
let generateText
let listContents
let ApiError
let marketingGenerationRequest
let messages
let compiledGeneration

before(async () => {
  vite = await createServer({ server: { middlewareMode: true, ws: false }, appType: 'custom' })
  App = (await vite.ssrLoadModule('/src/App.tsx')).default
  LanguageProvider = (await vite.ssrLoadModule('/src/hooks/useLanguage.tsx')).LanguageProvider
  MarketingGenerationForm = (await vite.ssrLoadModule('/src/components/MarketingGeneration.tsx')).MarketingGenerationForm
  const api = await vite.ssrLoadModule('/src/services/api.ts')
  generateText = api.generateText
  listContents = api.listContents
  ApiError = api.ApiError
  marketingGenerationRequest = (await vite.ssrLoadModule('/src/utils/marketingGeneration.ts')).marketingGenerationRequest
  messages = (await vite.ssrLoadModule('/src/i18n/messages.ts')).messages
  const component = new URL('../src/components/MarketingGeneration.tsx', import.meta.url)
  compiledGeneration = ts.transpileModule(await readFile(component, 'utf8'), {
    fileName: component.pathname,
    compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS },
  }).outputText
})

after(async () => vite?.close())

const campaign = {
  id: 7,
  title: 'Weekend offer',
  domain: 'marketing',
  objective: 'Grow local orders',
  language: 'both',
  status: 'draft',
  created_at: '2026-11-20T10:00:00Z',
}

const marketing = {
  ...campaign,
  campaign_type: 'marketing',
  business_name: 'Cairo Bakery',
  offer_summary: 'Assorted pastry box',
  target_audience: 'Local families',
  budget: null,
  channels: [],
  brief: null,
}

function content(id, language, generation, created) {
  return {
    id,
    campaign_id: campaign.id,
    generation_id: generation,
    language,
    content_type: 'text_package',
    review_status: 'draft',
    content: {
      headline: 'Weekend pastry box',
      slogan: 'Make it a pastry weekend',
      awareness_message: 'Order an assorted pastry box.',
      social_caption: 'Pick up your box this weekend.',
      call_to_action: 'Order today.',
    },
    provider: 'fake',
    model: 'local-test',
    prompt_version: 'marketing-text-v1',
    input_snapshot: {},
    source_references: [],
    created_at: created,
  }
}

function renderCampaign(id, queryClient) {
  return renderToStaticMarkup(
    createElement(MemoryRouter, { initialEntries: ['/campaigns/' + id] },
      createElement(QueryClientProvider, { client: queryClient },
        createElement(LanguageProvider, null, createElement(App)))),
  )
}

function renderDetail(record, history = []) {
  const queryClient = new QueryClient()
  queryClient.setQueryData(['campaign', record.id], record)
  queryClient.setQueryData(['contents', record.id], history)
  try {
    return renderCampaign(record.id, queryClient)
  } finally {
    queryClient.clear()
  }
}

function renderForm(overrides = {}) {
  return renderToStaticMarkup(createElement(LanguageProvider, null,
    createElement(MarketingGenerationForm, {
      targetAudience: marketing.target_audience,
      isPending: false,
      isSuccess: false,
      error: null,
      onGenerate() {},
      ...overrides,
    }),
  ))
}

function findForm(element) {
  if (element?.type === 'form') return element
  for (const child of Children.toArray(element?.props?.children)) {
    const form = findForm(child)
    if (form) return form
  }
}

// Hold one set of hook values so the real submit handler can run before a
// rerender. TanStack Query and the HTTP client still handle the mutation.
function generationForm(queryClient, beforeMutate = () => {}) {
  const submissions = []
  const stateWrites = []
  const exports = {}
  const modules = {
    react: {
      useId: () => 'test',
      useRef: (current) => ({ current }),
      useState: (value) => [value, (next) => stateWrites.push(next)],
    },
    'react/jsx-runtime': jsxRuntime,
    '@tanstack/react-query': {
      useQueryClient: () => queryClient,
      useMutation(options) {
        const observer = new MutationObserver(queryClient, options)
        return {
          ...observer.getCurrentResult(),
          mutate(data) {
            beforeMutate()
            submissions.push(observer.mutate(data))
          },
        }
      },
    },
    '../hooks/useLanguage': { useLanguage: () => ({ t: (key) => messages.en[key] }) },
    '../services/api': { ApiError, generateText },
    '../utils/marketingGeneration': { marketingGenerationRequest },
  }
  runInNewContext(compiledGeneration, {
    exports,
    require(name) {
      assert.ok(name in modules, 'Unexpected test import ' + name)
      return modules[name]
    },
  })
  const panel = exports.default({ campaign: marketing })
  const form = findForm(panel.type(panel.props))
  assert.ok(form)
  return { submit: () => form.props.onSubmit({ preventDefault() {} }), submissions, stateWrites }
}

test('marketing uses an empty JSON body by default and sends a trimmed override through the same endpoint', async (t) => {
  const requests = []
  const response = { campaign_id: 7, contents: [content(1, 'english', 'first', '2026-11-21T10:00:00Z')] }
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    requests.push({ path: new URL(url).pathname, method: init.method, body: init.body })
    return Response.json(response, { status: 201 })
  })

  for (const audience of ['', '  ', '  Weekend shoppers  ']) {
    assert.deepEqual(await generateText(7, marketingGenerationRequest(audience)), response)
  }
  assert.deepEqual(requests.map(({ body }) => body), ['{}', '{}', '{"audience":"Weekend shoppers"}'])
  assert.ok(requests.every(({ path, method }) => (
    path === '/api/v1/campaigns/7/generate-text' && method === 'POST'
  )))
})

test('two same-render submits start one POST and the lock releases after success and failure', async (t) => {
  const queryClient = new QueryClient()
  t.after(() => queryClient.clear())
  const requests = []
  const saved = { campaign_id: campaign.id, contents: [content(1, 'english', 'first', '2026-11-21T10:00:00Z')] }
  t.mock.method(globalThis, 'fetch', (url, init) => {
    assert.equal(new URL(url).pathname, '/api/v1/campaigns/7/generate-text')
    assert.equal(init.method, 'POST')
    assert.equal(init.body, '{}')
    const reply = Promise.withResolvers()
    requests.push(reply)
    return reply.promise
  })
  const form = generationForm(queryClient)
  assert.equal(requests.length, 0)

  form.submit()
  form.submit()
  await turn()
  assert.equal(requests.length, 1)
  assert.equal(form.submissions.length, 1)
  requests[0].resolve(Response.json(saved, { status: 201 }))
  await form.submissions[0]

  form.submit()
  await turn()
  assert.equal(requests.length, 2)
  const rejected = assert.rejects(form.submissions[1], { status: 502 })
  requests[1].resolve(Response.json({ detail: 'mock provider failure' }, { status: 502 }))
  await rejected

  form.submit()
  await turn()
  assert.equal(requests.length, 3)
  requests[2].resolve(Response.json(saved, { status: 201 }))
  await form.submissions[2]
})

test('a synchronous mutation startup failure releases the lock and reports a safe error', async (t) => {
  const queryClient = new QueryClient()
  t.after(() => queryClient.clear())
  const saved = { campaign_id: campaign.id, contents: [] }
  const fetch = t.mock.method(globalThis, 'fetch', async () => Response.json(saved, { status: 201 }))
  let failStart = true
  const form = generationForm(queryClient, () => {
    if (failStart) {
      failStart = false
      throw new Error('PRIVATE_MARKER')
    }
  })

  form.submit()
  assert.equal(fetch.mock.callCount(), 0)
  assert.equal(form.stateWrites.at(-1).message, 'Could not start generation')
  form.submit()
  await form.submissions[0]
  assert.equal(fetch.mock.callCount(), 1)
})

test('generation aborts an initial history GET and renders the saved draft despite a late stale response', { timeout: 5000 }, async (t) => {
  const queryClient = new QueryClient()
  const queryKey = ['contents', campaign.id]
  queryClient.setQueryData(['campaign', campaign.id], marketing)
  const post = Promise.withResolvers()
  const refetchStarted = Promise.withResolvers()
  const historyRequests = []
  const otherRequests = []
  let postSignal
  const draft = content(1, 'english', 'first', '2026-11-21T10:00:00Z')
  t.mock.method(globalThis, 'fetch', (input, init) => {
    const url = new URL(input)
    if (init.method === 'POST') {
      assert.equal(url.pathname, '/api/v1/campaigns/7/generate-text')
      postSignal = init.signal
      return post.promise
    }
    const reply = Promise.withResolvers()
    const request = { reply, signal: init.signal }
    if (url.pathname === '/api/v1/campaigns/7/contents' && url.searchParams.get('skip') === '0') {
      historyRequests.push(request)
      if (historyRequests.length === 2) refetchStarted.resolve()
    } else {
      otherRequests.push(request)
    }
    // The mock intentionally allows the original response to arrive after abort.
    return reply.promise
  })
  const observers = [
    [campaign.id, 0, queryKey],
    [campaign.id, 100, [...queryKey, 100]],
    [8, 0, ['contents', 8]],
  ].map(([id, skip, key]) => new QueryObserver(queryClient, {
    queryKey: key,
    queryFn: ({ signal }) => listContents(id, skip, undefined, signal),
  }))
  const unsubscribe = observers.map((observer) => observer.subscribe(() => {}))
  t.after(() => {
    unsubscribe.forEach((stop) => stop())
    queryClient.clear()
  })
  assert.equal(historyRequests.length, 1)
  assert.equal(otherRequests.length, 2)

  const form = generationForm(queryClient)
  form.submit()
  await turn()
  post.resolve(Response.json({ campaign_id: campaign.id, contents: [draft] }, { status: 201 }))
  await refetchStarted.promise
  assert.equal(postSignal, undefined)
  assert.equal(historyRequests[0].signal.aborted, true)
  assert.equal(historyRequests[1].signal.aborted, false)
  assert.ok(otherRequests.every(({ signal }) => !signal.aborted))

  historyRequests[1].reply.resolve(Response.json([draft]))
  await form.submissions[0]
  historyRequests[0].reply.resolve(Response.json([]))
  otherRequests.forEach(({ reply }) => reply.resolve(Response.json([])))
  await turn()

  assert.deepEqual(queryClient.getQueryData(queryKey), [draft])
  const html = renderCampaign(campaign.id, queryClient)
  assert.ok(html.includes(messages.en['det.drafts']))
  assert.equal(html.split(draft.content.headline).length - 1, 1)
})

test('stored marketing type selects the marketing form and legacy rows still require an audience', () => {
  const marketingHtml = renderDetail({ ...marketing, domain: 'traffic_safety' })
  assert.ok(marketingHtml.includes(messages.en['marketingGen.override']))
  assert.match(marketingHtml, /<button type="submit" class="btn btn-gold">Generate draft<\/button>/)
  assert.ok(marketingHtml.indexOf(messages.en['marketingGen.cost']) < marketingHtml.indexOf('>Generate draft<'))

  for (const record of [
    { ...campaign, domain: 'traffic_safety' },
    campaign,
    { ...campaign, campaign_type: null },
  ]) {
    const html = renderDetail(record)
    assert.match(html, /<input id="audience"/)
    assert.match(html, /<select id="tone"/)
    assert.match(html, /<button[^>]+disabled="">Generate text<\/button>/)
    assert.ok(!html.includes(messages.en['marketingGen.title']))
  }

  const missingAudience = renderForm({ targetAudience: null })
  assert.ok(missingAudience.includes(messages.en['marketingGen.audienceRequired']))
  assert.match(missingAudience, /<input[^>]+required=""/)
  assert.match(missingAudience, /<button[^>]+disabled="">Generate draft<\/button>/)
})

test('marketing pending, saved, and safe error states are rendered', () => {
  const pending = renderForm({ isPending: true })
  assert.match(pending, /<input[^>]+disabled=""/)
  assert.match(pending, /<button[^>]+disabled="">Generate draft<\/button>/)
  assert.match(pending, /role="status"><p[^>]*>Generating/)
  assert.ok(renderForm({ isSuccess: true }).includes(messages.en['marketingGen.saved']))

  for (const [status, key] of [[422, 'marketingGen.invalid'], [502, 'marketingGen.rejected']]) {
    const html = renderForm({ error: new ApiError(status, 'PRIVATE_MARKER') })
    assert.match(html, /role="alert"/)
    assert.ok(html.includes(messages.en[key]))
    assert.ok(!html.includes('PRIVATE_MARKER'))
  }
  const keys = Object.keys(messages.en).filter((key) => key.startsWith('marketingGen.'))
  assert.ok(keys.every((key) => /[\u0600-\u06ff]/.test(messages.ar[key])))
})

test('latest bilingual drafts keep all fields and edit and review actions while history is read-only', () => {
  const html = renderDetail(marketing, [
    content(1, 'english', 'first', '2026-11-20T10:00:00Z'),
    content(2, 'english', 'latest', '2026-11-21T10:00:00Z'),
    content(3, 'arabic', 'latest', '2026-11-21T10:00:00Z'),
  ])
  for (const label of ['Headline', 'Slogan', 'Awareness message', 'Social caption', 'Call to action']) {
    assert.equal(html.split('<label>' + label + '</label>').length - 1, 3)
  }
  assert.match(html, /class="pkg" dir="ltr"/)
  assert.match(html, /class="pkg ar" dir="rtl"/)
  assert.ok(html.includes('Generation history'))
  for (const action of ['Edit', 'Approve', 'Reject']) {
    assert.equal(html.split('>' + action + '</button>').length - 1, 2)
  }
  assert.ok(html.includes(messages.en['common.draft']))
})
