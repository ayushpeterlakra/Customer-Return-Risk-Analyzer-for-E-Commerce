import type { ReviewStatus, RiskLevel } from '../../types/api'
import { REVIEW_LABEL, RISK_LABEL } from '../../lib/format'

const RISK_STYLE: Record<RiskLevel, string> = {
  HIGH: 'bg-red-50 text-red-700 ring-red-600/20',
  MEDIUM: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  LOW: 'bg-green-50 text-green-700 ring-green-600/20',
}

const REVIEW_STYLE: Record<ReviewStatus, string> = {
  PENDING_REVIEW: 'bg-slate-100 text-slate-700 ring-slate-500/20',
  UNDER_INVESTIGATION: 'bg-indigo-50 text-indigo-700 ring-indigo-600/20',
  REVIEWED: 'bg-green-50 text-green-700 ring-green-600/20',
  ESCALATED: 'bg-red-50 text-red-700 ring-red-600/20',
}

const base = 'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap'

export function RiskBadge({ level }: { level: RiskLevel | null }) {
  if (!level) return <span className={`${base} bg-slate-50 text-slate-500 ring-slate-300`}>Not scored</span>
  return (
    <span className={`${base} ${RISK_STYLE[level]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {RISK_LABEL[level]}
    </span>
  )
}

export function ReviewBadge({ status }: { status: ReviewStatus | null }) {
  if (!status) return <span className="text-xs text-slate-400">No review</span>
  return <span className={`${base} ${REVIEW_STYLE[status]}`}>{REVIEW_LABEL[status]}</span>
}

export function Tag({ children, tone = 'slate' }: { children: React.ReactNode; tone?: 'slate' | 'red' | 'amber' }) {
  const tones = {
    slate: 'bg-slate-100 text-slate-700 ring-slate-500/10',
    red: 'bg-red-50 text-red-700 ring-red-600/20',
    amber: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  }
  return <span className={`${base} ${tones[tone]}`}>{children}</span>
}

export function ScoreBar({ score, level }: { score: number | null; level: RiskLevel | null }) {
  if (score == null) return <span className="text-slate-400">—</span>
  const color = level === 'HIGH' ? 'bg-risk-high' : level === 'MEDIUM' ? 'bg-risk-medium' : 'bg-risk-low'
  return (
    <div className="flex items-center gap-2">
      <span className="w-7 text-right font-semibold tabular-nums">{score}</span>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100" aria-hidden>
        <div className={`h-full ${color}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  )
}
