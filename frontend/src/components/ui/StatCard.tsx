import type { LucideIcon } from 'lucide-react'
import { Skeleton } from './States'

interface Props {
  label: string
  value: string
  hint?: string
  icon: LucideIcon
  tone?: 'default' | 'high' | 'medium' | 'low'
  loading?: boolean
}

const TONES = {
  default: 'bg-indigo-50 text-primary',
  high: 'bg-red-50 text-risk-high',
  medium: 'bg-amber-50 text-risk-medium',
  low: 'bg-green-50 text-risk-low',
}

export function StatCard({ label, value, hint, icon: Icon, tone = 'default', loading }: Props) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">{label}</p>
        <span className={`rounded-lg p-1.5 ${TONES[tone]}`}>
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      </div>
      {loading ? (
        <Skeleton className="mt-3 h-7 w-20" />
      ) : (
        <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      )}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}
