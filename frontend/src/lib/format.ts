import type { ReviewStatus, RiskLevel } from '../types/api'

export const RISK_COLORS: Record<RiskLevel, string> = {
  HIGH: '#dc2626',
  MEDIUM: '#d97706',
  LOW: '#16a34a',
}

export const RISK_LABEL: Record<RiskLevel, string> = { HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low' }

export const REVIEW_LABEL: Record<ReviewStatus, string> = {
  PENDING_REVIEW: 'Pending review',
  UNDER_INVESTIGATION: 'Under investigation',
  REVIEWED: 'Reviewed',
  ESCALATED: 'Escalated',
}

export const REVIEW_STATUSES: ReviewStatus[] = ['PENDING_REVIEW', 'UNDER_INVESTIGATION', 'REVIEWED', 'ESCALATED']

export const CHART_PRIMARY = '#4f46e5'
export const CHART_SECONDARY = '#94a3b8'

const numberFmt = new Intl.NumberFormat('en-US')
const moneyFmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })

export const fmtNumber = (n: number | null | undefined) => (n == null ? '—' : numberFmt.format(n))
export const fmtMoney = (n: number | string | null | undefined) => (n == null ? '—' : moneyFmt.format(Number(n)))
export const fmtPct = (n: number | null | undefined, digits = 1) => (n == null ? '—' : `${n.toFixed(digits)}%`)

/** Dates from the API are ISO strings; date-only values are parsed as UTC to avoid off-by-one days. */
export function fmtDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = value.length === 10 ? new Date(`${value}T00:00:00Z`) : new Date(value)
  return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: value.length === 10 ? 'UTC' : undefined })
}

export function fmtDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export const humanize = (code: string) =>
  code
    .toLowerCase()
    .split('_')
    .map((w, i) => (i === 0 ? w.charAt(0).toUpperCase() + w.slice(1) : w))
    .join(' ')
