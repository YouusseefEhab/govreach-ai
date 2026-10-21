import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { ApiError, generateText, listContents } from '../src/services/api.ts'
import { generationFormSchema } from '../src/services/generation-form.ts'

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })

const generationId = 'f23507de-84ac-46a6-9f07-a44918edf4b2'
function item(id = 15, language = 'arabic') {
  return {
    id, campaign_id: 27, generation_id: generationId, language, content_type: 'text_package',
    review_status: 'draft', content: { headline: 'Test', slogan: 'Test', awareness_message: 'Test', social_caption: 'Test', call_to_action: 'Test' },
    provider: 'fake', model: 'test', prompt_version: 'test', input_snapshot: {}, source_references: [], created_at: '2026-10-21T12:00:00Z',
  }
}

test('generation validates audiences, Unicode limits, and supported tones', () => {
  for (const audience of ['', '   ', 'ع'.repeat(301)]) assert.equal(generationFormSchema.safeParse({ audience, tone: 'informative' }).success, false)
  assert.equal(generationFormSchema.safeParse({ audience: 'Valid', tone: 'casual' }).success, false)
  assert.deepEqual(generationFormSchema.parse({ audience: ' السواقين ', tone: 'encouraging' }), { audience: 'السواقين', tone: 'encouraging' })
  assert.ok(generationFormSchema.safeParse({ audience: '🚗'.repeat(300), tone: 'formal' }).success)
})

test('generation sends only audience/tone once and permits the backend timeout to finish', async () => {
  let calls = 0
  const realTimeout = AbortSignal.timeout
  let timeoutMs = 0
  AbortSignal.timeout = (ms) => { timeoutMs = ms; return realTimeout(ms) }
  try {
    globalThis.fetch = async (url, options) => {
      calls++
      assert.equal(String(url), 'http://localhost:8000/api/v1/campaigns/27/generate-text')
      assert.equal(options?.method, 'POST')
      assert.deepEqual(JSON.parse(options?.body as string), { audience: 'السواقين', tone: 'informative' })
      return Response.json({ campaign_id: 27, contents: [item(), item(16, 'english')] }, { status: 201 })
    }
    const result = await generateText(27, { audience: 'السواقين', tone: 'informative' })
    assert.equal(result.contents.length, 2)
    assert.equal(calls, 1)
    assert.equal(timeoutMs, 120_000)
  } finally { AbortSignal.timeout = realTimeout }
})

test('generation errors 502/503/504 and lost connections do not replay paid requests', async () => {
  for (const status of [502, 503, 504, 0]) {
    let calls = 0
    globalThis.fetch = async () => {
      calls++
      if (status === 0) throw new TypeError('Lost connection')
      return Response.json({}, { status })
    }
    await assert.rejects(generateText(27, { audience: 'Drivers', tone: 'formal' }), (error: unknown) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.status, status || null)
      return true
    })
    assert.equal(calls, 1)
  }
})

test('generation rejects duplicate languages and inconsistent saved metadata', async () => {
  const first = item()
  for (const contents of [
    [first, item(16)],
    [{ ...first, campaign_id: 28 }],
    [first, { ...item(16, 'english'), generation_id: 'd38887e2-7ed3-48c5-b2cd-f163ed126f02' }],
  ]) {
    globalThis.fetch = async () => Response.json({ campaign_id: 27, contents })
    await assert.rejects(generateText(27, { audience: 'Drivers', tone: 'informative' }), ApiError)
  }
})

test('history is independently paginated and never sends a generation POST', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(String(url), 'http://localhost:8000/api/v1/campaigns/27/contents?skip=20&limit=20')
    assert.ok(!options?.method || options.method === 'GET')
    return Response.json([item()])
  }
  assert.equal((await listContents(27, 20, 20))[0].generation_id, generationId)
})

test('browser timeout requires checking saved history before resubmission', async () => {
  const realTimeout = AbortSignal.timeout
  AbortSignal.timeout = () => AbortSignal.abort(new DOMException('Timeout', 'TimeoutError'))
  globalThis.fetch = async () => { throw new DOMException('Timeout', 'TimeoutError') }
  try {
    await assert.rejects(generateText(27, { audience: 'Drivers', tone: 'formal' }), (error: unknown) => {
      assert.ok(error instanceof ApiError)
      assert.ok(error.message.includes('راجع المحتوى المحفوظ'))
      return true
    })
  } finally { AbortSignal.timeout = realTimeout }
})
