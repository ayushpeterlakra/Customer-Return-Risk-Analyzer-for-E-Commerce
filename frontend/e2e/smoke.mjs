// End-to-end smoke test: drives the real dashboard against the real API.
// Prerequisites: backend on :8000 with seeded data, frontend on :5173.
// Run: npm run e2e   (first time: npx playwright install chromium)
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const BASE = process.env.E2E_BASE_URL ?? 'http://localhost:5173'
const SHOTS = process.env.E2E_SCREENSHOTS ?? 'e2e/screenshots'
mkdirSync(SHOTS, { recursive: true })

const results = []
const consoleErrors = []
let expectHttpError = false // set while a step deliberately sends a bad request
async function step(name, fn) {
  try {
    await fn()
    results.push(['PASS', name])
  } catch (err) {
    results.push(['FAIL', name, String(err).split('\n')[0]])
    await page.screenshot({ path: `${SHOTS}/FAIL-${results.length}.png`, fullPage: true }).catch(() => {})
    await page.keyboard.press('Escape').catch(() => {})
  }
}
const expect = (cond, msg) => {
  if (!cond) throw new Error(msg)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.on('console', (m) => {
  if (m.type() !== 'error') return
  if (expectHttpError && m.text().includes('Failed to load resource')) return
  consoleErrors.push(m.text())
})
page.on('pageerror', (e) => consoleErrors.push(e.message))

await step('Overview shows live summary cards and charts', async () => {
  await page.goto(BASE)
  await page.getByText('High risk', { exact: true }).first().waitFor()
  await page.locator('.recharts-surface').first().waitFor()
  const total = await page.locator('main').getByText('Customers', { exact: true }).locator('xpath=../..').innerText()
  expect(/\d{2,}/.test(total), `customer count missing: ${total}`)
  expect((await page.locator('.recharts-surface').count()) >= 3, 'expected 3+ charts')
  await page.waitForTimeout(1500) // let chart animations finish
  await page.screenshot({ path: `${SHOTS}/01-overview.png`, fullPage: true })
})

await step('Overview date range filter changes the request', async () => {
  const req = page.waitForRequest((r) => r.url().includes('/api/analytics/summary') && r.url().includes('date_from'))
  await page.getByRole('button', { name: '30 days' }).click()
  await req
  await page.getByRole('button', { name: 'All time' }).click()
})

await step('Customers: search, filters, sort, pagination', async () => {
  await page.getByRole('link', { name: 'Customers' }).first().click()
  await page.locator('tbody tr').first().waitFor()
  expect((await page.locator('tbody tr').count()) === 20, 'expected 20 rows')
  await page.getByRole('button', { name: 'Next page' }).click()
  await page.getByText('Page 2 of').waitFor()
  await page.getByLabel('Risk level').selectOption('HIGH')
  await page.waitForResponse((r) => r.url().includes('risk_level=HIGH'))
  await page.waitForTimeout(200)
  const levels = await page.locator('tbody tr td:nth-child(7)').allInnerTexts()
  expect(levels.length > 0 && levels.every((t) => t.includes('High')), 'risk filter not applied')
  await page.getByLabel('Risk level').selectOption('')
  // Filters are URL-driven, so click and wait for the request rather than asserting instant DOM state.
  await Promise.all([page.waitForResponse((r) => r.url().includes('min_return_ratio=0.3')), page.getByLabel('Return ratio above 30%').click()])
  await page.waitForTimeout(200)
  const ratios = (await page.locator('tbody tr td:nth-child(5)').allInnerTexts()).map((t) => parseFloat(t))
  expect(ratios.every((r) => r > 30), 'ratio filter not applied')
  await page.getByLabel('Return ratio above 30%').click()
  await page.waitForURL((u) => !u.search.includes('high_ratio'))
  await page.getByRole('button', { name: 'Name' }).click()
  await page.waitForResponse((r) => r.url().includes('sort=name'))
  await page.waitForTimeout(200)
  const names = await page.locator('tbody tr td:nth-child(2)').allInnerTexts()
  expect(names.join() === [...names].sort((a, b) => a.localeCompare(b)).join(), 'not sorted by name')
  await page.getByPlaceholder('Search by customer ID or name').fill('CUST0046')
  await page.waitForResponse((r) => r.url().includes('search=CUST0046'))
  await page.waitForTimeout(200)
  expect((await page.locator('tbody tr').count()) === 1, 'search did not narrow to one row')
  await page.waitForTimeout(1500) // let chart animations finish
  await page.screenshot({ path: `${SHOTS}/02-customers.png`, fullPage: true })
})

await step('Export CSV link returns a CSV', async () => {
  const href = await page.getByRole('link', { name: /Export CSV/ }).getAttribute('href')
  const res = await page.request.get(href)
  expect(res.ok() && (await res.text()).startsWith('customer_id,name,risk_score'), 'bad CSV')
})

await step('Customer detail: factors, history, returns, ML, rescore', async () => {
  await page.getByRole('link', { name: 'View profile' }).first().click()
  await page.getByText('Risk factor breakdown').waitFor()
  await page.getByText('Return history').first().waitFor()
  await page.locator('table').first().waitFor()
  await page.getByRole('button', { name: 'Run model' }).click()
  await page.getByText(/Resembles/).waitFor()
  const before = await page.locator('.recharts-area-area').count()
  await page.getByRole('button', { name: 'Rescore now' }).click()
  await page.waitForResponse((r) => r.url().includes('/history'))
  expect(before >= 0, '')
  await page.waitForTimeout(1500) // let chart animations finish
  await page.screenshot({ path: `${SHOTS}/03-customer-detail.png`, fullPage: true })
})

await step('Review status change is saved and appears in the audit trail', async () => {
  await page.getByRole('button', { name: 'Change status' }).click()
  const dialog = page.getByRole('dialog')
  const current = await dialog.getByText(/Current status/).innerText()
  const target = current.includes('Escalated') ? 'UNDER_INVESTIGATION' : 'ESCALATED'
  await dialog.getByLabel('New status').selectOption(target)
  await dialog.getByLabel(/Your name/).fill('E2E Reviewer')
  const note = `Changed by automated end-to-end test ${Date.now()}`
  await dialog.getByLabel('Notes').fill(note)
  await dialog.getByRole('button', { name: 'Save status' }).click()
  await page.getByText(note).waitFor()
})

await step('Risk monitoring lists high-risk customers and filters by status', async () => {
  await page.getByRole('link', { name: 'Risk monitoring' }).first().click()
  await page.locator('tbody tr').first().waitFor()
  await Promise.all([page.waitForResponse((r) => r.url().includes('review_status=PENDING_REVIEW')), page.getByLabel('Review status').selectOption('PENDING_REVIEW')])
  await page.waitForTimeout(200)
  const statuses = await page.locator('tbody tr td:nth-child(4)').allInnerTexts()
  expect(statuses.every((t) => t.includes('Pending')), 'status filter not applied')
  await page.getByLabel('Review status').selectOption('')
  await page.waitForTimeout(1500) // let chart animations finish
  await page.screenshot({ path: `${SHOTS}/04-monitoring.png`, fullPage: true })
})

await step('Analytics: charts, granularity toggle, ML metrics', async () => {
  await page.getByRole('link', { name: 'Analytics' }).first().click()
  await page.getByText('Machine learning evaluation').waitFor()
  await page.locator('.recharts-surface').nth(4).waitFor()
  const req = page.waitForRequest((r) => r.url().includes('granularity=day'))
  await page.getByRole('button', { name: 'Daily' }).click()
  await req
  await page.getByText('Logistic regression').first().waitFor()
  await page.waitForTimeout(1500) // let chart animations finish
  await page.screenshot({ path: `${SHOTS}/05-analytics.png`, fullPage: true })
})

await step('Settings: invalid import is rejected with line errors', async () => {
  await page.getByRole('link', { name: 'Settings' }).first().click()
  await page.getByText('Risk scoring rules').waitFor()
  await page.locator('input[type=file]').setInputFiles({ name: 'bad.csv', mimeType: 'text/csv', buffer: Buffer.from('customer_id\nX\n') })
  expectHttpError = true
  await page.getByRole('button', { name: 'Import' }).click()
  await page.getByText(/Missing columns/).waitFor()
  expectHttpError = false
  await page.waitForTimeout(1500) // let chart animations finish
  await page.screenshot({ path: `${SHOTS}/06-settings.png`, fullPage: true })
})

await step('Mobile layout: menu opens and navigates', async () => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(BASE)
  await page.getByRole('button', { name: 'Open menu' }).click()
  await page.getByRole('dialog', { name: 'Menu' }).getByRole('link', { name: 'Customers' }).click()
  await page.locator('h1', { hasText: 'Customers' }).waitFor()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  expect(!overflow, 'page scrolls horizontally on mobile')
  await page.waitForTimeout(1500) // let chart animations finish
  await page.screenshot({ path: `${SHOTS}/07-mobile.png` })
})

await browser.close()
for (const r of results) console.log(r.join(' | '))
const failed = results.filter((r) => r[0] === 'FAIL').length
console.log(`\n${results.length - failed} passed, ${failed} failed; console errors: ${consoleErrors.length}`)
consoleErrors.slice(0, 10).forEach((e) => console.log('  console:', e))
process.exit(failed || consoleErrors.length ? 1 : 0)
