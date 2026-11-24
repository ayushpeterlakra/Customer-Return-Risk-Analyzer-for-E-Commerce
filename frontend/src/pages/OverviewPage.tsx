import { AlertOctagon, AlertTriangle, CheckCircle2, Package, Percent, RotateCcw, Users } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/endpoints'
import { CategoryBarChart, RiskDonut, TrendChart } from '../components/charts/Charts'
import { ChartFrame } from '../components/charts/ChartFrame'
import { ReviewBadge, ScoreBar } from '../components/ui/Badge'
import { Card, CardHeader } from '../components/ui/Card'
import { DateRangeFilter } from '../components/ui/DateRangeFilter'
import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/States'
import { useApi } from '../hooks/useApi'
import { fmtNumber, fmtPct } from '../lib/format'
import type { DateRange } from '../types/api'

export function OverviewPage() {
  const [range, setRange] = useState<DateRange>({})
  const valid = !(range.date_from && range.date_to && range.date_from > range.date_to)
  const r = valid ? range : {}
  const summary = useApi(() => api.summary(r), [r.date_from, r.date_to])
  const dist = useApi(() => api.riskDistribution(), [])
  const cats = useApi(() => api.returnsByCategory(r), [r.date_from, r.date_to])
  const trends = useApi(() => api.returnTrends('week', r), [r.date_from, r.date_to])
  const top = useApi(() => api.highRisk(1), [])
  const s = summary.data
  const ranged = Boolean(r.date_from || r.date_to)

  return (
    <>
      <PageHeader
        title="Overview"
        description="Return behaviour across all customers. Risk scores flag patterns for review; they are not findings of fraud."
        actions={<DateRangeFilter value={range} onChange={setRange} />}
      />
      {summary.error && (
        <Card className="mb-6">
          <ErrorState message={summary.error} onRetry={summary.reload} />
        </Card>
      )}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Customers" value={fmtNumber(s?.total_customers)} icon={Users} loading={summary.loading} />
        <StatCard label="Orders" value={fmtNumber(s?.total_orders)} hint={ranged ? 'In selected range' : 'Excluding cancelled'} icon={Package} loading={summary.loading} />
        <StatCard label="Returns" value={fmtNumber(s?.total_returns)} hint={ranged ? 'In selected range' : 'Excluding rejected'} icon={RotateCcw} loading={summary.loading} />
        <StatCard label="Avg return ratio" value={fmtPct(s ? s.average_return_ratio * 100 : null)} hint="Per customer, all time" icon={Percent} loading={summary.loading} />
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="High risk" value={fmtNumber(s?.high_risk_customers)} hint="Flagged for manual review" icon={AlertOctagon} tone="high" loading={summary.loading} />
        <StatCard label="Medium risk" value={fmtNumber(s?.medium_risk_customers)} hint="Score 41–70" icon={AlertTriangle} tone="medium" loading={summary.loading} />
        <StatCard label="Low risk" value={fmtNumber(s?.low_risk_customers)} hint="Score 0–40" icon={CheckCircle2} tone="low" loading={summary.loading} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <ChartFrame title="Weekly return trend" subtitle={ranged ? 'Selected range' : 'All time'} loading={trends.loading} error={trends.error} empty={!trends.data?.length} onRetry={trends.reload}>
            <TrendChart data={trends.data ?? []} />
          </ChartFrame>
        </div>
        <ChartFrame title="Customers by risk level" subtitle="Latest assessment" loading={dist.loading} error={dist.error} empty={!dist.data?.some((d) => d.count)} onRetry={dist.reload}>
          <RiskDonut data={dist.data ?? []} />
        </ChartFrame>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <ChartFrame title="Returns by product category" subtitle="Hover a bar for the category return rate" loading={cats.loading} error={cats.error} empty={!cats.data?.length} onRetry={cats.reload}>
            <CategoryBarChart data={cats.data ?? []} />
          </ChartFrame>
        </div>
        <Card>
          <CardHeader title="Highest-risk customers" subtitle="Top of the review queue" actions={<Link to="/monitoring" className="text-xs font-medium text-primary hover:underline">View all</Link>} />
          {top.error ? (
            <ErrorState message={top.error} onRetry={top.reload} />
          ) : top.loading ? (
            <TableSkeleton rows={5} cols={2} />
          ) : !top.data?.items.length ? (
            <EmptyState title="No high-risk customers" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {top.data.items.slice(0, 6).map((c) => (
                <li key={c.customer_id}>
                  <Link to={`/customers/${c.customer_id}`} className="flex items-center justify-between gap-3 px-5 py-3 hover:bg-slate-50">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-800">{c.name}</p>
                      <p className="truncate text-xs text-slate-500">
                        {c.customer_id} · {c.top_factors[0]?.factor ?? 'No factors'}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <ScoreBar score={c.risk_score} level={c.risk_level} />
                      <ReviewBadge status={c.review_status} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  )
}
