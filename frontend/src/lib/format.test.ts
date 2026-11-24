import { describe, expect, it } from 'vitest'
import { fmtDate, fmtMoney, fmtPct, humanize } from './format'

describe('formatters', () => {
  it('formats date-only strings without timezone drift', () => {
    expect(fmtDate('2026-01-01')).toBe('01 Jan 2026')
  })
  it('handles missing values', () => {
    expect(fmtDate(null)).toBe('—')
    expect(fmtPct(undefined)).toBe('—')
    expect(fmtMoney(null)).toBe('—')
  })
  it('formats money and percentages', () => {
    expect(fmtMoney('109950')).toBe('₹1,09,950.00')
    expect(fmtPct(41.666)).toBe('41.7%')
  })
  it('humanizes enum codes', () => {
    expect(humanize('NOT_AS_DESCRIBED')).toBe('Not as described')
  })
})
