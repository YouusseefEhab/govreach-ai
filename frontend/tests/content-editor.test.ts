import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { ApiError, getContent, updateContent } from '../src/services/api.ts'
import { changedTextFields, contentFormSchema, textFields } from '../src/services/content-form.ts'
import type { TextPackage } from '../src/services/types.ts'

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })
const content: TextPackage = { headline: 'Original', slogan: 'Slogan', awareness_message: 'Message', social_caption: 'Caption', call_to_action: 'Action' }
const row = {
  id: 15, campaign_id: 27, generation_id: 'f23507de-84ac-46a6-9f07-a44918edf4b2', language: 'arabic',
  review_status: 'approved', content_type: 'text_package', content, provider: 'fake', model: 'test', prompt_version: 'test',
  input_snapshot: {}, source_references: [], created_at: '2026-10-21T12:00:00Z',
}

test('each required text field obeys its backend Unicode length limit', () => {
  for (const field of Object.keys(textFields) as (keyof TextPackage)[]) {
    assert.equal(contentFormSchema.safeParse({ ...content, [field]: '   ' }).success, false)
    assert.equal(contentFormSchema.safeParse({ ...content, [field]: '🚗'.repeat(textFields[field].limit) }).success, true)
    assert.equal(contentFormSchema.safeParse({ ...content, [field]: 'ع'.repeat(textFields[field].limit + 1) }).success, false)
  }
})

test('partial saves omit unchanged fields and trimming never sends empty edits', () => {
  assert.deepEqual(changedTextFields(content, content), {})
  const values = contentFormSchema.parse({ ...content, headline: ' New headline ' })
  assert.deepEqual(changedTextFields(content, values), { headline: 'New headline' })
})

test('edit and approval are separate PATCH requests; editing receives confirmed draft status', async () => {
  const requests: unknown[] = []
  globalThis.fetch = async (url, options) => {
    assert.equal(String(url), 'http://localhost:8000/api/v1/contents/15')
    assert.equal(options?.method, 'PATCH')
    const body = JSON.parse(options?.body as string)
    requests.push(body)
    return Response.json(body.content
      ? { ...row, content: { ...content, ...body.content }, review_status: 'draft' }
      : { ...row, review_status: body.review_status })
  }
  const edited = await updateContent(15, { content: { headline: 'Updated' } })
  assert.equal(edited.review_status, 'draft')
  assert.equal(edited.content.slogan, content.slogan)
  assert.equal((await updateContent(15, { review_status: 'approved' })).review_status, 'approved')
  assert.deepEqual(requests, [{ content: { headline: 'Updated' } }, { review_status: 'approved' }])
})

test('reject is persisted independently; failed review requests are not replayed', async () => {
  globalThis.fetch = async () => Response.json({ ...row, review_status: 'rejected' })
  assert.equal((await updateContent(15, { review_status: 'rejected' })).review_status, 'rejected')
  let calls = 0
  globalThis.fetch = async () => { calls++; return Response.json({}, { status: 503 }) }
  await assert.rejects(updateContent(15, { review_status: 'approved' }), ApiError)
  assert.equal(calls, 1)
})

test('read and save reject a mismatched record or missing draft reset', async () => {
  globalThis.fetch = async () => Response.json({ ...row, id: 16 })
  await assert.rejects(getContent(15), ApiError)
  globalThis.fetch = async () => Response.json(row)
  await assert.rejects(updateContent(15, { content: { headline: 'Changed' } }), ApiError)
})
