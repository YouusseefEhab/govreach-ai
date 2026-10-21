import assert from 'node:assert/strict'
import { test } from 'node:test'
import { campaignFormSchema } from '../src/services/campaign-form.ts'

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
