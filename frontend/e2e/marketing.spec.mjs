import { expect, test } from '@playwright/test'

const campaignsPath = '/api/v1/campaigns'
const generationPath = /\/api\/v1\/campaigns\/\d+\/generate-text$/
const token = process.env.MARKETPILOT_E2E_TOKEN

async function testStatus(request) {
  const response = await request.get('/__e2e/status', {
    headers: { 'X-MarketPilot-E2E': token },
  })
  expect(response.ok()).toBe(true)
  const status = await response.json()
  expect(status.database).toBe('marketpilot_integration_test')
  expect(status.schema).toMatch(/^marketpilot_it_[a-f0-9]{32}$/)
  expect(status.provider).toBe('fake')
  return status
}

test.beforeEach(async ({ context, request, baseURL }) => {
  await testStatus(request)
  await context.route('**/*', (route) =>
    new URL(route.request().url()).origin === baseURL ? route.continue() : route.abort())
})

const button = (page, name) => page.getByRole('button', { name, exact: true })
const packages = (page) => page.locator('.pkg')
const override = (page) => page.getByLabel('Audience override (optional)')
const campaignPath = (page) => campaignsPath + '/' + new URL(page.url()).pathname.split('/').at(-1)

function responseFor(page, method, path) {
  return page.waitForResponse((response) => {
    const pathname = new URL(response.url()).pathname
    return response.request().method() === method &&
      (typeof path === 'string' ? pathname === path : path.test(pathname))
  })
}

async function createCampaign(page, title, marketing = true) {
  await page.goto('/campaigns/new')
  await expect(page.getByLabel('Campaign type')).toHaveValue('marketing')
  if (!marketing) await page.getByLabel('Campaign type').selectOption('traffic_safety')
  await page.getByLabel('Campaign title').fill(title)
  await page.getByLabel('Objective', { exact: true }).fill(
    marketing ? 'Grow weekend pickup orders' : 'Encourage seat belt use',
  )
  if (marketing) {
    await page.getByLabel('Business name').fill('Cairo Bakery')
    await page.getByLabel('Offer summary').fill('Assorted pastry box for weekend pickup')
    await page.getByLabel('Target audience').fill('Local families')
    await page.getByLabel('Budget amount (optional)').fill('1200.50')
    await page.getByLabel('Currency', { exact: true }).selectOption('EGP')
    await page.getByRole('checkbox', { name: 'Email' }).check()
  }
  const [response] = await Promise.all([
    responseFor(page, 'POST', campaignsPath),
    button(page, 'Create campaign').click(),
  ])
  expect(response.status()).toBe(201)
  if (!marketing) expect(response.request().postDataJSON()).not.toHaveProperty('campaign_type')
  await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
}

async function generate(page, action, body, status = 201) {
  const [response] = await Promise.all([responseFor(page, 'POST', generationPath), action()])
  expect(response.request().postDataJSON()).toEqual(body)
  expect(response.status()).toBe(status)
  return response.json()
}

async function savedHistory(page) {
  const response = await page.request.get(campaignPath(page) + '/contents')
  expect(response.ok()).toBe(true)
  return response.json()
}

test('marketing CRUD, bilingual generation, review and history persist across reload', async ({ page }) => {
  const title = 'Pastry weekend browser campaign'
  await createCampaign(page, title)
  await expect(page.getByText('1200.50 EGP', { exact: true })).toBeVisible()
  await page.goto('/campaigns')
  const campaignRow = page.getByRole('row').filter({ hasText: title })
  await expect(campaignRow).toContainText('Cairo Bakery')
  await campaignRow.getByRole('link', { name: 'Open' }).click()

  await button(page, 'Edit campaign details').click()
  await page.getByLabel('Business name').fill('Cairo Weekend Bakery')
  await page.getByLabel('Budget amount (optional)').clear()
  const [updated] = await Promise.all([
    responseFor(page, 'PATCH', campaignPath(page)),
    page.locator('form.campaign-form').getByRole('button', { name: 'Save changes' }).click(),
  ])
  expect(updated.status()).toBe(200)
  expect(updated.request().postDataJSON()).toEqual({ business_name: 'Cairo Weekend Bakery', budget: null })
  expect(await updated.json()).toMatchObject({ business_name: 'Cairo Weekend Bakery', budget: null })
  await expect(page.getByText('1200.50 EGP', { exact: true })).toHaveCount(0)

  const audience = override(page)
  await expect(audience).toHaveAccessibleDescription('Leave blank to use the campaign’s saved target audience.')
  await expect(page.getByText(/live AI provider may charge/)).toBeVisible()
  await audience.focus()
  const first = await generate(page, () => audience.press('Enter'), {})
  expect(first.contents.map((row) => row.language).sort()).toEqual(['arabic', 'english'])
  for (const row of first.contents) {
    expect(row).toMatchObject({
      provider: 'fake',
      review_status: 'draft',
      source_references: [],
      input_snapshot: { audience: 'Local families', tone: 'informative' },
    })
  }
  await expect(packages(page)).toHaveCount(2)
  const english = page.locator('.pkg[dir="ltr"]')
  const arabic = page.locator('.pkg[dir="rtl"]')
  await expect(english.locator('.pkg__field')).toHaveCount(5)
  await expect(arabic.locator('.pkg__field')).toHaveCount(5)
  const edited = 'Edited weekend pastry headline'
  await button(english, 'Edit').click()
  await english.getByRole('textbox').first().fill(edited)
  await button(english, 'Save changes').click()
  await expect(english.getByText(edited, { exact: true })).toBeVisible()
  await button(english, 'Approve').click()
  await expect(english.getByText('Approved', { exact: true })).toBeVisible()
  await expect(arabic.getByText('Draft', { exact: true })).toBeVisible()

  await audience.fill('  Office workers  ')
  const second = await generate(page, () => button(page, 'Generate draft').click(), { audience: 'Office workers' })
  expect(second.contents[0].input_snapshot).toMatchObject({
    audience: 'Office workers', target_audience: 'Local families',
  })
  expect(second.contents[0].generation_id).not.toBe(first.contents[0].generation_id)
  await page.reload()
  await expect(page.getByText('Cairo Weekend Bakery', { exact: true })).toBeVisible()
  await expect(page.getByText('1200.50 EGP', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Generation history' })).toBeVisible()
  await expect(packages(page)).toHaveCount(4)
  const reviewedHistory = english.filter({ hasText: edited })
  await expect(reviewedHistory.getByText('Approved', { exact: true })).toBeVisible()
  await expect(button(reviewedHistory, 'Edit')).toHaveCount(0)
})

test('legacy generation keeps its required audience, tone and traffic sources', async ({ page }) => {
  await createCampaign(page, 'Seat belt browser campaign', false)
  const audience = page.getByLabel('Audience', { exact: true })
  const tone = page.getByLabel('Tone', { exact: true })
  await expect(button(page, 'Generate text')).toBeDisabled()
  await expect(tone).toHaveValue('informative')
  await audience.fill('Drivers in Egypt')
  await tone.selectOption('formal')
  const saved = await generate(page, () => button(page, 'Generate text').click(), {
    audience: 'Drivers in Egypt', tone: 'formal',
  })
  expect(saved.contents[0]).toMatchObject({
    provider: 'fake', prompt_version: 'traffic-text-v2-sourced',
    source_references: expect.arrayContaining([expect.objectContaining({ id: 'who-seat-belts' })]),
  })

  const legacy = await page.request.post(campaignsPath, {
    data: { domain: 'marketing', title: 'Historical domain browser campaign', objective: 'Legacy rows' },
  })
  expect(legacy.status()).toBe(201)
  const record = await legacy.json()
  expect(record).not.toHaveProperty('campaign_type')
  await page.goto('/campaigns/' + record.id)
  await expect(button(page, 'Generate text')).toBeDisabled()
  await expect(tone).toHaveValue('informative')
  await expect(override(page)).toHaveCount(0)
})

test('marketing failures stay safe and Arabic RTL labels remain accessible', async ({ page, request }) => {
  await createCampaign(page, 'Safe errors browser campaign')
  await generate(page, () => button(page, 'Generate draft').click(), {})
  const before = await savedHistory(page)
  expect(before).toHaveLength(2)
  const callCount = (await testStatus(request)).provider_calls
  const pastedCredential = 'Authorization: Bearer integration-fake-bearer-0123456789'
  await override(page).fill(pastedCredential)
  const blocked = await generate(page, () => button(page, 'Generate draft').click(), {
    audience: pastedCredential,
  }, 422)
  expect(JSON.stringify(blocked)).not.toContain(pastedCredential)
  await expect(page.getByRole('alert')).toContainText('Remove any pasted API keys')
  await expect(page.getByRole('alert')).not.toContainText('integration-fake-bearer')
  expect((await testStatus(request)).provider_calls).toBe(callCount)
  expect(await savedHistory(page)).toEqual(before)

  await override(page).fill('E2E unsupported claim')
  await generate(page, () => button(page, 'Generate draft').click(), { audience: 'E2E unsupported claim' }, 502)
  await expect(page.getByRole('alert')).toContainText('The generated draft could not be accepted')
  await expect(page.getByRole('alert')).not.toContainText('Save 75%')
  expect(await savedHistory(page)).toEqual(before)

  await override(page).fill('E2E provider failure')
  await generate(page, () => button(page, 'Generate draft').click(), { audience: 'E2E provider failure' }, 503)
  await expect(page.getByRole('alert')).toContainText('The generation service is unavailable')
  await expect(page.getByRole('alert')).not.toContainText('E2E_INTERNAL_PROVIDER_DETAIL')
  expect(await savedHistory(page)).toEqual(before)

  await button(page, 'ع').click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'ar')
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  const arabicAudience = page.getByLabel('جمهور بديل (اختياري)')
  await expect(arabicAudience).toHaveAccessibleDescription('اترك الحقل فارغًا لاستخدام الجمهور المستهدف المحفوظ في الحملة.')
  await expect(page.getByRole('alert')).toContainText('خدمة التوليد غير متاحة')
  await arabicAudience.focus()
  await page.keyboard.press('Tab')
  await expect(button(page, 'توليد مسودة')).toBeFocused()
})

test('same-turn submissions send one POST and refresh past an older delayed GET', async ({ page }) => {
  await createCampaign(page, 'Delayed generations browser campaign')
  const path = campaignPath(page)
  const staleReady = Promise.withResolvers()
  const postReady = Promise.withResolvers()
  const releaseStale = Promise.withResolvers()
  const releasePost = Promise.withResolvers()
  let staleRequest
  let aborted = false
  let reads = 0
  let posts = 0
  page.on('requestfailed', (request) => { if (request === staleRequest) aborted = true })
  await page.route((url) => url.pathname === path + '/contents', async (route) => {
    if (++reads !== 1) {
      await route.continue()
      return
    }
    staleRequest = route.request()
    const response = await route.fetch({ maxRedirects: 0 })
    staleReady.resolve(await response.json())
    await releaseStale.promise
    if (!aborted) await route.fulfill({ response }).catch(() => {})
  })
  await page.route((url) => url.pathname === path + '/generate-text', async (route) => {
    posts++
    expect(route.request().postDataJSON()).toEqual({})
    const response = await route.fetch({ maxRedirects: 0 })
    postReady.resolve(response.status())
    await releasePost.promise
    await route.fulfill({ response })
  })

  try {
    await page.reload()
    expect(await staleReady.promise).toEqual([])
    await override(page).fill('   ')
    expect(posts).toBe(0)
    await page.locator('form').filter({ has: button(page, 'Generate draft') }).evaluate((form) => {
      form.requestSubmit()
      form.requestSubmit()
    })
    expect(await postReady.promise).toBe(201)
    await expect(button(page, 'Generate draft')).toBeDisabled()
    releasePost.resolve()
    await expect(packages(page)).toHaveCount(2)
    await expect.poll(() => aborted).toBe(true)
    expect(reads).toBeGreaterThanOrEqual(2)
    releaseStale.resolve()
    await expect(packages(page)).toHaveCount(2)
    expect(posts).toBe(1)
    expect(await savedHistory(page)).toHaveLength(2)
  } finally {
    releaseStale.resolve()
    releasePost.resolve()
  }
})
