import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { ApiError, apiRequest, checkBackend, listCampaigns } from '../src/services/api.ts'

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })

test('campaign reads encode pagination and validate bilingual records', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(String(url), 'http://localhost:8000/api/v1/campaigns?skip=20&limit=20')
    assert.equal(new Headers(options?.headers).get('Accept'), 'application/json')
    return Response.json([{
      id: 7, title: 'حزامك أمانك', objective: 'Encourage seat belts',
      domain: 'traffic_safety', language: 'both', status: 'draft',
      created_at: '2026-10-13T17:59:49.190369Z',
    }])
  }
  const campaigns = await listCampaigns(20, 20)
  assert.equal(campaigns[0].title, 'حزامك أمانك')
})

test('health response follows the actual FastAPI contract', async () => {
  globalThis.fetch = async () => Response.json({ status: 'healthy' })
  assert.deepEqual(await checkBackend(), { status: 'healthy' })
})

test('missing records and malformed successful payloads are controlled errors', async () => {
  for (const body of [null, {}, [{ id: 7 }]]) {
    globalThis.fetch = async () => Response.json(body)
    await assert.rejects(listCampaigns(0, 20), (error: unknown) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.status, 200)
      return true
    })
  }
})

test('FastAPI validation errors retain field paths without exposing input values', async () => {
  globalThis.fetch = async () => Response.json({ detail: [{
    loc: ['body', 'content', 'headline'], msg: 'String should have at least 1 character',
    input: 'private input',
  }] }, { status: 422 })
  await assert.rejects(apiRequest('/example'), (error: unknown) => {
    assert.ok(error instanceof ApiError)
    assert.equal(error.status, 422)
    assert.deepEqual(error.fields, [{
      path: 'content.headline', message: 'String should have at least 1 character',
    }])
    assert.ok(!JSON.stringify(error).includes('private input'))
    return true
  })
})

test('HTTP errors are safe and requests are never automatically replayed', async () => {
  for (const status of [404, 502, 503, 504]) {
    let calls = 0
    globalThis.fetch = async () => {
      calls++
      return Response.json({ detail: 'internal provider or database information' }, { status })
    }
    await assert.rejects(apiRequest('/example', { method: 'POST', body: '{}' }), (error: unknown) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.status, status)
      assert.ok(!error.message.includes('internal'))
      return true
    })
    assert.equal(calls, 1)
  }
})

test('empty DELETE responses do not attempt JSON decoding', async () => {
  globalThis.fetch = async (_url, options) => {
    assert.equal(options?.method, 'DELETE')
    return new Response(null, { status: 204 })
  }
  assert.equal(await apiRequest('/example', { method: 'DELETE' }), undefined)
})

test('network failures become actionable errors and cancellation stays cancellation', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  await assert.rejects(checkBackend(), (error: unknown) => {
    assert.ok(error instanceof ApiError)
    assert.equal(error.status, null)
    return true
  })
  const controller = new AbortController()
  controller.abort()
  globalThis.fetch = async () => { throw new DOMException('Aborted', 'AbortError') }
  await assert.rejects(checkBackend(controller.signal), { name: 'AbortError' })
})
