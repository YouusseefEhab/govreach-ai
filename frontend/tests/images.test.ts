import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { ApiError } from '../src/services/api.ts'
import { clearImageAttempt, createImageAttempt, generateImage, getImage, imageFileUrl, imageRequestSchema,
  listImages, loadImageAttempt, reviewImage, saveImageAttempt } from '../src/services/images.ts'

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })
const request = { source_content_id: 15, visual_brief: 'Parked car, correct seat belts, no text', style: 'illustration' as const }
export function savedImage(overrides: Record<string, unknown> = {}) {
  return {
    id: 51, campaign_id: 27, source_content_id: 15, idempotency_key: 'image_test_1', request_state: 'ready', review_status: 'draft', source_is_current: true,
    source_snapshot: { language: 'arabic', content: { headline: '<script>unsafe</script>' } }, source_references: [],
    visual_brief: request.visual_brief, style: request.style, provider: 'fake', model: 'fake-image-v1', prompt_version: 'traffic-image-v1',
    mime_type: 'image/png', width: 32, height: 32, byte_count: 99, failure_code: null,
    created_at: '2026-11-08T12:00:00Z', updated_at: '2026-11-08T12:00:00Z', ...overrides,
  }
}

test('image briefs require a source, supported style and bounded Unicode text', () => {
  for (const data of [{ ...request, visual_brief: '  ' }, { ...request, source_content_id: 0 },
    { ...request, visual_brief: 'ع'.repeat(2001) }, { ...request, style: 'unknown' }, { ...request, provider: 'other' }]) {
    assert.equal(imageRequestSchema.safeParse(data).success, false)
  }
  assert.equal(imageRequestSchema.parse({ ...request, visual_brief: '  مشهد آمن  ' }).visual_brief, 'مشهد آمن')
  assert.ok(imageRequestSchema.safeParse({ ...request, visual_brief: '🚗'.repeat(2000) }).success)
})

test('generation sends one request and preserves its identity on explicit replay', async () => {
  let calls = 0
  const timeouts: number[] = []
  const realTimeout = AbortSignal.timeout
  AbortSignal.timeout = (ms) => { timeouts.push(ms); return realTimeout(ms) }
  try {
    globalThis.fetch = async (url, options) => {
      calls++
      assert.equal(String(url), 'http://localhost:8000/api/v1/campaigns/27/generate-image')
      assert.equal(options?.method, 'POST')
      assert.equal(new Headers(options?.headers).get('Idempotency-Key'), 'image_test_1')
      assert.deepEqual(JSON.parse(options?.body as string), request)
      return Response.json(savedImage(), { status: calls === 1 ? 201 : 200 })
    }
    assert.equal((await generateImage(27, request, 'image_test_1')).id, 51)
    assert.equal(calls, 1)
    assert.equal((await generateImage(27, request, 'image_test_1')).id, 51)
    assert.equal(calls, 2)
    assert.deepEqual(timeouts, [150_000, 150_000])
  } finally { AbortSignal.timeout = realTimeout }
})

test('a 200 replay can describe failure or uncertainty and never implies an image is ready', async () => {
  for (const state of ['reserved', 'generating', 'failed', 'outcome_unknown']) {
    let calls = 0
    globalThis.fetch = async () => { calls++; return Response.json(savedImage({ request_state: state, mime_type: null, width: null, height: null, byte_count: null })) }
    assert.equal((await generateImage(27, request, 'image_test_1')).request_state, state)
    assert.equal(calls, 1)
  }
})

test('image errors and lost connections do not automatically repeat requests', async () => {
  for (const status of [409, 422, 502, 503, 504, 0]) {
    let calls = 0
    globalThis.fetch = async () => { calls++; if (!status) throw new Error('private details'); return Response.json({ detail: 'private provider response' }, { status }) }
    await assert.rejects(generateImage(27, request, 'image_test_1'), (error: unknown) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.status, status || null)
      assert.ok(!error.message.includes('private'))
      return true
    })
    assert.equal(calls, 1)
  }
})

test('malformed or mismatched generated-image metadata is rejected', async () => {
  for (const row of [savedImage({ campaign_id: 28 }), savedImage({ idempotency_key: 'wrong' }), savedImage({ source_content_id: 16 }),
    savedImage({ width: null }), savedImage({ height: 20 }), savedImage({ mime_type: 'image/svg+xml' }),
    savedImage({ request_state: 'failed', review_status: 'approved' })]) {
    globalThis.fetch = async () => Response.json(row)
    await assert.rejects(generateImage(27, request, 'image_test_1'), ApiError)
  }
})

test('invalid request identity fails before a provider endpoint is contacted', async () => {
  let calls = 0
  globalThis.fetch = async () => { calls++; throw new Error('Unexpected request') }
  for (const key of ['', 'invalid/key', 'x'.repeat(129)]) await assert.rejects(generateImage(27, request, key))
  assert.equal(calls, 0)
})

test('image history and metadata are reads with separate pagination and identity checks', async () => {
  const urls: string[] = []
  globalThis.fetch = async (url, options) => {
    assert.ok(!options?.method || options.method === 'GET')
    urls.push(String(url))
    return Response.json(urls.length === 1 ? [savedImage()] : savedImage())
  }
  assert.equal((await listImages(27, 20, 20))[0].id, 51)
  assert.equal((await getImage(51)).id, 51)
  assert.deepEqual(urls, ['http://localhost:8000/api/v1/campaigns/27/images?skip=20&limit=20', 'http://localhost:8000/api/v1/images/51'])
  globalThis.fetch = async () => Response.json([savedImage({ campaign_id: 28 })])
  await assert.rejects(listImages(27), ApiError)
  globalThis.fetch = async () => Response.json(savedImage({ id: 52 }))
  await assert.rejects(getImage(51), ApiError)
})

test('image approval is a separate PATCH and requires a current ready response', async () => {
  let calls = 0
  globalThis.fetch = async (url, options) => {
    calls++
    assert.equal(String(url), 'http://localhost:8000/api/v1/images/51')
    assert.equal(options?.method, 'PATCH')
    assert.deepEqual(JSON.parse(options?.body as string), { review_status: 'approved' })
    return Response.json(savedImage({ review_status: 'approved' }))
  }
  assert.equal((await reviewImage(51, 'approved')).review_status, 'approved')
  assert.equal(calls, 1)
  globalThis.fetch = async () => Response.json(savedImage({ review_status: 'approved', source_is_current: false }))
  await assert.rejects(reviewImage(51, 'approved'), ApiError)
})

test('rejection and draft review preserve source staleness and do not generate', async () => {
  for (const status of ['rejected', 'draft'] as const) {
    globalThis.fetch = async (_url, options) => {
      assert.equal(options?.method, 'PATCH')
      assert.deepEqual(JSON.parse(options?.body as string), { review_status: status })
      return Response.json(savedImage({ review_status: status, source_is_current: false }))
    }
    assert.equal((await reviewImage(51, status)).source_is_current, false)
  }
})

test('file links use only validated IDs and controlled download queries', () => {
  assert.equal(imageFileUrl(51), 'http://localhost:8000/api/v1/images/51/file')
  assert.equal(imageFileUrl(51, true), 'http://localhost:8000/api/v1/images/51/file?download=true')
  for (const id of [0, -1, NaN, Infinity]) assert.throws(() => imageFileUrl(id))
})

test('attempt storage retains original inputs and key across a recovery read', () => {
  const values = new Map<string, string>()
  const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value) }, removeItem: (key: string) => { values.delete(key) } }
  const attempt = createImageAttempt(270, request, () => 'saved_identity')
  assert.equal(saveImageAttempt(attempt, storage), true)
  assert.deepEqual(loadImageAttempt(270, storage), attempt)
  assert.equal(loadImageAttempt(271, storage), null)
  clearImageAttempt(270, storage)
  assert.equal(loadImageAttempt(270, storage), null)
  assert.equal(values.size, 0)
})

test('unavailable storage preserves in-memory recovery and reports that reload persistence failed', () => {
  const blocked = { getItem: () => { throw new Error('Blocked') }, setItem: () => { throw new Error('Blocked') }, removeItem: () => { throw new Error('Blocked') } }
  const attempt = createImageAttempt(272, request, () => 'memory_identity')
  assert.equal(saveImageAttempt(attempt, blocked), false)
  assert.deepEqual(loadImageAttempt(272, blocked), attempt)
  clearImageAttempt(272, blocked)
  assert.equal(loadImageAttempt(272, blocked), null)
})

test('corrupt or cross-campaign saved attempts are ignored without any network action', () => {
  for (const raw of ['invalid json', JSON.stringify({ campaign_id: 274, key: 'x', request }), JSON.stringify({ campaign_id: 273, key: '../bad', request })]) {
    assert.equal(loadImageAttempt(273, { getItem: () => raw, setItem: () => {}, removeItem: () => {} }), null)
  }
})
