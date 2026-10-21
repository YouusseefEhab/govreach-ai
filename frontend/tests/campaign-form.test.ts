import assert from 'node:assert/strict'
import { test } from 'node:test'
import { campaignFormSchema, changedCampaignFields } from '../src/services/campaign-form.ts'

test('blank briefs and unsupported languages cannot be submitted', () => {
  for (const invalid of [
    { title: '   ', objective: 'Valid', language: 'both' },
    { title: 'Valid', objective: '\n\t', language: 'both' },
    { title: 'Valid', objective: 'Valid', language: 'french' },
  ]) assert.equal(campaignFormSchema.safeParse(invalid).success, false)
})

test('briefs are trimmed and title limits match Python Unicode character counts', () => {
  const valid = campaignFormSchema.parse({ title: ` ${'🚗'.repeat(255)} `, objective: ' هدف واضح ', language: 'arabic' })
  assert.equal([...valid.title].length, 255)
  assert.equal(valid.objective, 'هدف واضح')
  assert.equal(campaignFormSchema.safeParse({ ...valid, title: 'ع'.repeat(256) }).success, false)
  for (const language of ['arabic', 'english', 'both']) {
    assert.equal(campaignFormSchema.safeParse({ ...valid, language }).success, true)
  }
})

test('editing sends only changed fields and never rewrites domain or status', () => {
  const original = { id: 27, title: 'Original', objective: 'Keep this', language: 'both', domain: 'custom_domain', status: 'draft', created_at: '2026-10-21T12:00:00Z' }
  const same = campaignFormSchema.parse({ title: ' Original ', objective: 'Keep this', language: 'both' })
  assert.deepEqual(changedCampaignFields(original, same), {})
  assert.deepEqual(changedCampaignFields(original, { ...same, title: 'Updated' }), { title: 'Updated' })
  assert.deepEqual(changedCampaignFields(original, { ...same, language: 'arabic' }), { language: 'arabic' })
})
