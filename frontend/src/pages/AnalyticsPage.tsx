import { useState } from 'react'
import { api } from '../api/endpoints'
import { CategoryBarChart, RatioHistogram, ReasonsChart, RiskDonut, TrendChart } from '../components/charts/Charts'
import { ChartFrame } from '../components/charts/ChartFrame'
import { Card, CardHeader } from '../components/ui/Card'
import { DateRangeFilter } from '../components/ui/DateRangeFilter'
import { PageHeader } from '../components/ui/PageHeader'
import { EmptyState, Skeleton } from '../components/ui/States'
import { useApi } from '../hooks/useApi'
import { fmtDateTime, humanize } from '../lib/format'
import type { DateRange, ModelMetrics } from '../types/api'

function MetricsTable({ rows, selected }: { rows: ModelMetrics[]; selected: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr className="border-b border-slate-100 bg-slate-50/60 text-left text-xs font-medium text-slate-500">
            <th className="px-4 py-2">Model</th>
            <th className="px-4 py-2 text-right">Accuracy</th>
            <th className="px-4 py-2 text-right">Precision</th>
            <th className="px-4 py-2 text-right">Recall</th>
            <th className="px-4 py-2 text-right">F1</th>
            <th className="px-4 py-2">Confusion matrix (TN / FP / FN / TP)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((m) => (
            <tr key={m.model} className={m.model === selected ? 'bg-indigo-50/50' : ''}>
              <td className="px-4 py-2 font-medium">
                {humanize(m.model)}
                {m.model === selected && <span className="ml-2 text-xs text-primary">selected</span>}
              </td>
              <td className="px-4 py-2 text-right tabular-nums">{m.accuracy.toFixed(3)}</td>
              <td className="px-4 py-2 text-right tabular-nums">{m.precision.toFixed(3)}</td>
              <td className="px-4 py-2 text-right tabular-nums">{m.recall.toFixed(3)}</td>
              <td className="px-4 py-2 text-right tabular-nums">{m.f1.toFixed(3)}</td>
              <td className="px-4 py-2 font-mono text-xs">
                {m.confusion_matrix.true_negative} / {m.confusion_matrix.false_positive} / {m.confusion_matrix.false_negative} / {m.confusion_matrix.true_positive}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MlSection() {
  const { data, error, loading } = useApi(() => api.mlMetrics(), [])
  return (
    <Card className="mt-6">
      <CardHeader title="Machine learning evaluation" subtitle="Held-out test set from the last training run" />
      {loading ? (
        <div className="p-5"><Skeleton className="h-32" /></div>
      ) : error ? (
        <EmptyState title="No trained model yet" message={`${error} Then reload this page.`} />
      ) : data ? (
        <>
          <p className="border-b border-slate-100 bg-amber-50 px-5 py-3 text-xs text-amber-900">{data.data_source}</p>
          <MetricsTable rows={[...Object.values(data.models), data.rule_based_baseline]} selected={data.selected_model} />
          <div className="grid gap-6 p-5 text-sm text-slate-600 md:grid-cols-2">
            <div>
              <p className="font-medium text-slate-800">About these numbers</p>
              <p className="mt-1">
                Trained {fmtDateTime(data.trained_at)} on {data.dataset.train} customers, tested on {data.dataset.test} ({data.dataset.test_positives} with a suspicious synthetic profile). A small, synthetic test set makes these figures optimistic and unstable.
              </p>
              <p className="mt-2">
                <span className="font-medium text-slate-800">Recall</span> is the share of suspicious patterns caught; missing them costs money. <span className="font-medium text-slate-800">Precision</span> is the share of flagged customers who really fit a suspicious pattern; low precision sends honest customers to review. Both matter here.
              </p>
            </div>
            <div>
              <p className="font-medium text-slate-800">Most influential features (decision tree)</p>
              <ul className="mt-1 space-y-1">
                {data.decision_tree_importances.slice(0, 6).map(([name, value]) => (
                  <li key={name} className="flex items-center gap-2">
                    <span className="w-48 truncate">{humanize(name)}</span>
                    <span className="h-1.5 flex-1 rounded-full bg-slate-100">
                      <span className="block h-full rounded-full bg-primary" style={{ width: `${value * 100}%` }} />
                    </span>
                    <span className="w-10 text-right tabular-nums">{value.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      ) : null}
    </Card>
  )
}

export function AnalyticsPage() {
  const [range, setRange] = useState<DateRange>({})
  const [granularity, setGranularity] = useState<'day' | 'week'>('week')
  const valid = !(range.date_from && range.date_to && range.date_from > range.date_to)
  const r = valid ? range : {}
  const cats = useApi(() => api.returnsByCategory(r), [r.date_from, r.date_to])
  const trends = useApi(() => api.returnTrends(granularity, r), [granularity, r.date_from, r.date_to])
  const ratio = useApi(() => api.ratioDistribution(), [])
  const reasons = useApi(() => api.returnReasons(r), [r.date_from, r.date_to])
  const dist = useApi(() => api.riskDistribution(), [])

  return (
    <>
      <PageHeader title="Analytics" description="Return patterns by category, reason, time and customer." actions={<DateRangeFilter value={range} onChange={setRange} />} />
      <ChartFrame
        title="Return trends"
        subtitle="Orders, returns and mismatches per period"
        loading={trends.loading}
        error={trends.error}
        empty={!trends.data?.length}
        onRetry={trends.reload}
        height={300}
        actions={
          <div className="flex rounded-lg border border-slate-200 p-0.5 text-xs" role="group" aria-label="Granularity">
            {(['day', 'week'] as const).map((g) => (
              <button key={g} type="button" onClick={() => setGranularity(g)} aria-pressed={granularity === g} className={`rounded-md px-2.5 py-1 font-medium ${granularity === g ? 'bg-primary text-white' : 'text-slate-600 hover:bg-slate-100'}`}>
                {g === 'day' ? 'Daily' : 'Weekly'}
              </button>
            ))}
          </div>
        }
      >
        <TrendChart data={trends.data ?? []} />
      </ChartFrame>
      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <ChartFrame title="Returns by product category" loading={cats.loading} error={cats.error} empty={!cats.data?.length} onRetry={cats.reload}>
          <CategoryBarChart data={cats.data ?? []} />
        </ChartFrame>
        <ChartFrame title="Return reasons" subtitle="Vague = vague reason code with no explanation" loading={reasons.loading} error={reasons.error} empty={!reasons.data?.length} onRetry={reasons.reload}>
          <ReasonsChart data={reasons.data ?? []} />
        </ChartFrame>
        <ChartFrame title="Return ratio distribution" subtitle="Customers per return-ratio band, all time" loading={ratio.loading} error={ratio.error} empty={!ratio.data?.some((b) => b.customers)} onRetry={ratio.reload}>
          <RatioHistogram data={ratio.data ?? []} />
        </ChartFrame>
        <ChartFrame title="Customers by risk level" loading={dist.loading} error={dist.error} empty={!dist.data?.some((d) => d.count)} onRetry={dist.reload}>
          <RiskDonut data={dist.data ?? []} />
        </ChartFrame>
      </div>
      <MlSection />
    </>
  )
}
