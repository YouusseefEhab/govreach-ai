import { defineConfig } from '@playwright/test'

const baseURL = process.env.MARKETPILOT_E2E_URL
const token = process.env.MARKETPILOT_E2E_TOKEN
if (!/^http:\/\/127\.0\.0\.1:[1-9][0-9]*$/.test(baseURL ?? '') || !/^[a-f0-9]{32}$/.test(token ?? '')) {
  throw new Error('Start the browser tests through the isolated backend pytest harness.')
}

const channel = process.env.MARKETPILOT_E2E_BROWSER ?? 'chrome'
if (!['chrome', 'msedge'].includes(channel)) throw new Error('Select the installed chrome or msedge browser.')

export default defineConfig({
  testDir: '.',
  workers: 1,
  reporter: 'list',
  use: { baseURL, channel, serviceWorkers: 'block' },
})
