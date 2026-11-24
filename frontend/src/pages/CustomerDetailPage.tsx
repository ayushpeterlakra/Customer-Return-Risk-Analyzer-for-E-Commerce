import { AlertTriangle, ArrowLeft, Brain, Calendar, Package, RefreshCw, RotateCcw, ShieldAlert, Wallet } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/endpoints'
import { toErrorMessage } from '../api/client'
import { ScoreHistoryChart } from '../components/charts/Charts'
import { ChartFrame } from '../components/charts/ChartFrame'
import { ReviewPanel } from '../components/ReviewPanel'
import { RiskBadge, Tag } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card, CardHeader } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { StatCard } from '../components/ui/StatCard'
import { EmptyState, ErrorState, Skeleton, TableSkeleton } from '../components/ui/States'
import { useApi } from '../hooks/useApi'
import { RISK_COLORS, fmtDate, fmtDateTime, fmtMoney, fmtPct, humanize } from '../lib/format'
import type { Assessment, MlPrediction, ReturnItem } from '../types/api'

function RiskBreakdown({ a }: { a: Assessment }) {
  return (
    <div className="space-y-4 p-5">
      <div className="flex items-center gap-4">
        <div className="relative h-20 w-20 shrink-0">
          <svg viewBox="0 0 36 36" className="h-20 w-20 -rotate-90" aria-hidden>
            <circle cx="18" cy="18" r="15.9" fill="none" stroke="#f1f5f9" strokeWidth="3.5" />
            <circle cx="18" cy="18" r="15.9" fill="none" stroke={RISK_COLORS[a.risk_level]} strokeWidth="3.5" strokeDasharray={`${a.risk_score} 100`} strokeLinecap="round" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-xl font-semibold tabular-nums">{a.risk_score}</span>
        </div>
        <div>
          <RiskBadge level={a.risk_level} />
          {a.requires_manual_review && <p className="mt-1 text-xs font-medium text-risk-high">Flagged for manual review</p>}
          <p className="mt-1 text-xs text-slate-500">
            Rule-based score · rules {a.config_version} · {fmtDateTime(a.assessed_at)}
          </p>
        </div>
      </div>
      {a.risk_factors.length === 0 ? (
        <p className="text-sm text-slate-600">No risk rules fired for this customer.</p>
      ) : (
        <ul className="space-y-3">
          {a.risk_factors.map((f) => (
            <li key={f.rule_id}>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium text-slate-800">{f.factor}</span>
                <span className="font-semibold tabular-nums text-slate-900">+{f.contribution}</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden>
                <div className="h-full bg-primary" style={{ width: `${Math.min(100, f.contribution)}%` }} />
              </div>
              <p className="mt-1 text-xs text-slate-500">{f.description}</p>
            </li>
          ))}
        </ul>
      )}
      {a.notes.length > 0 && (
        <ul className="space-y-1 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
          {a.notes.map((n) => (
            <li key={n}>• {n}</li>
          ))}
        </ul>
      )}
      <p className="text-xs text-slate-400">A high score marks behaviour worth reviewing. It does not establish that the customer committed fraud.</p>
    </div>
  )
}

function MlPanel({ customerId, ruleScore }: { customerId: string; ruleScore: number | null }) {
  const [result, setResult] = useState<MlPrediction | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const run = async () => {
    setBusy(true)
    setError(null)
    try {
      setResult(await api.mlPredict(customerId))
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Card>
      <CardHeader title="ML model estimate" subtitle="Separate from the rule-based score" actions={<Button onClick={run} disabled={busy} icon={<Brain className="h-4 w-4" />}>{busy ? 'Running…' : result ? 'Run again' : 'Run model'}</Button>} />
      <div className="p-5 text-sm">
        {error ? (
          <p role="alert" className="text-red-700">{error}</p>
        ) : !result ? (
          <p className="text-slate-500">Run the trained model to see how closely this customer's behaviour resembles the synthetic suspicious patterns it learned.</p>
        ) : (
          <div className="space-y-2">
            <p className="text-3xl font-semibold tabular-nums">{(result.probability_suspicious_pattern * 100).toFixed(1)}%</p>
            <p className="text-slate-700">
              {humanize(result.predicted_label.replace(/ /g, '_'))} <span className="text-slate-400">(model: {humanize(result.model)}, threshold {(result.threshold * 100).toFixed(0)}%)</span>
            </p>
            <p className="text-xs text-slate-500">
              The rule score ({ruleScore ?? '—'}/100) adds points from published rules. This number is a model probability; the two are shown side by side and never combined.
            </p>
            <p className="text-xs text-slate-400">{result.disclaimer}</p>
          </div>
        )}
      </div>
    </Card>
  )
}

function ReturnTimeline({ returns }: { returns: ReturnItem[] }) {
  const items = [...returns].reverse().slice(-12)
  const maxDays = Math.max(14, ...items.map((r) => r.days_to_return))
  return (
    <div className="space-y-2 p-5">
      {items.map((r) => (
        <div key={r.return_id} className="grid grid-cols-[88px_1fr_56px] items-center gap-3 text-xs">
          <span className="text-slate-500">{fmtDate(r.return_date)}</span>
          <div className="relative h-5 rounded bg-slate-50" title={`${r.days_to_return} day(s) from delivery to return`}>
            <div className={`absolute inset-y-0 left-0 rounded ${r.days_to_return < 2 ? 'bg-amber-400' : 'bg-indigo-300'}`} style={{ width: `${Math.max(3, (r.days_to_return / maxDays) * 100)}%` }} />
            <span className="absolute inset-y-0 left-2 flex items-center truncate text-[11px] text-slate-700">
              {r.product_name}
              {r.mismatch_flag && ' · mismatch'}
            </span>
          </div>
          <span className="text-right tabular-nums text-slate-600">{r.days_to_return}d</span>
        </div>
      ))}
      <p className="pt-1 text-[11px] text-slate-400">Bar length = days from delivery to return (amber = under 2 days). Latest {items.length} returns.</p>
    </div>
  )
}

export function CustomerDetailPage() {
  const { customerId = '' } = useParams()
  const detail = useApi(() => api.customer(customerId), [customerId])
  const returns = useApi(() => api.customerReturns(customerId), [customerId])
  const orders = useApi(() => api.customerOrders(customerId), [customerId])
  const history = useApi(() => api.riskHistory(customerId), [customerId])
  const [rescoring, setRescoring] = useState(false)
  const [rescoreError, setRescoreError] = useState<string | null>(null)

  const rescore = async () => {
    setRescoring(true)
    setRescoreError(null)
    try {
      await api.assess(customerId)
      detail.reload()
      history.reload()
    } catch (err) {
      setRescoreError(toErrorMessage(err))
    } finally {
      setRescoring(false)
    }
  }

  if (detail.error) {
    return (
      <>
        <Link to="/customers" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft className="h-4 w-4" /> Customers
        </Link>
        <Card>
          <ErrorState message={detail.error} onRetry={detail.reload} />
        </Card>
      </>
    )
  }
  const d = detail.data
  const a = d?.latest_assessment ?? null

  return (
    <>
      <Link to="/customers" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="h-4 w-4" /> Customers
      </Link>
      <PageHeader
        title={d ? d.name : 'Loading…'}
        description={d ? `${d.customer_id} · ${d.email} · customer since ${fmtDate(d.created_at)}` : undefined}
        actions={
          <>
            {a && <RiskBadge level={a.risk_level} />}
            <Button onClick={rescore} disabled={rescoring || !d} icon={<RefreshCw className={`h-4 w-4 ${rescoring ? 'animate-spin' : ''}`} />}>
              Rescore now
            </Button>
          </>
        }
      />
      {rescoreError && <p role="alert" className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{rescoreError}</p>}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard label="Orders" value={String(d?.total_orders ?? '—')} icon={Package} loading={detail.loading} />
        <StatCard label="Returns" value={String(d?.total_returns ?? '—')} icon={RotateCcw} loading={detail.loading} />
        <StatCard label="Return ratio" value={fmtPct(d?.return_percentage)} icon={Calendar} tone={d && d.return_percentage > 40 ? 'high' : 'default'} loading={detail.loading} />
        <StatCard label="Mismatches" value={String(d?.mismatch_count ?? '—')} icon={AlertTriangle} tone={d && d.mismatch_count > 0 ? 'medium' : 'default'} loading={detail.loading} />
        <StatCard label="Refunded" value={fmtMoney(d?.total_refunded)} hint={d ? `of ${fmtMoney(d.total_order_value)} ordered` : undefined} icon={Wallet} loading={detail.loading} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <Card>
            <CardHeader title="Risk factor breakdown" subtitle="How each rule contributed to the score" />
            {detail.loading ? <div className="p-5"><Skeleton className="h-40" /></div> : a ? <RiskBreakdown a={a} /> : <EmptyState title="Not scored yet" message="Use Rescore now to compute a score." />}
          </Card>
          <ChartFrame title="Risk score history" subtitle="Every stored assessment" loading={history.loading} error={history.error} empty={!history.data?.length} onRetry={history.reload} height={200}>
            <ScoreHistoryChart data={history.data ?? []} />
          </ChartFrame>
        </div>
        <div className="space-y-6">
          {d && <ReviewPanel customerId={d.customer_id} current={d.review_status} onChanged={detail.reload} />}
          <MlPanel customerId={customerId} ruleScore={a?.risk_score ?? null} />
          <Card>
            <CardHeader title="Product categories" subtitle="Orders and returns per category" />
            {d && d.categories.length ? (
              <ul className="divide-y divide-slate-100 text-sm">
                {d.categories.map((c) => (
                  <li key={c.category} className="flex justify-between px-5 py-2">
                    <span>{c.category}</span>
                    <span className="tabular-nums text-slate-600">
                      {c.returns} / {c.orders} returned
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title="No orders" />
            )}
          </Card>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-1">
          <CardHeader title="Return timeline" subtitle="Delivery to return, per return" />
          {returns.loading ? <TableSkeleton rows={5} cols={1} /> : returns.data?.items.length ? <ReturnTimeline returns={returns.data.items} /> : <EmptyState title="No returns" />}
        </Card>
        <Card className="xl:col-span-2">
          <CardHeader title="Return history" subtitle={returns.data ? `${returns.data.total} returns` : undefined} />
          {returns.error ? (
            <ErrorState message={returns.error} onRetry={returns.reload} />
          ) : returns.loading ? (
            <TableSkeleton rows={5} cols={6} />
          ) : !returns.data?.items.length ? (
            <EmptyState title="This customer has not returned anything" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/60 text-left text-xs font-medium text-slate-500">
                    <th className="px-4 py-2">Product</th>
                    <th className="px-4 py-2">Delivered</th>
                    <th className="px-4 py-2">Returned</th>
                    <th className="px-4 py-2 text-right">Days</th>
                    <th className="px-4 py-2">Reason</th>
                    <th className="px-4 py-2">Flags</th>
                    <th className="px-4 py-2 text-right">Refund</th>
                    <th className="px-4 py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {returns.data.items.map((r) => (
                    <tr key={r.return_id} className={r.mismatch_flag ? 'bg-red-50/40' : ''}>
                      <td className="min-w-[180px] px-4 py-2">
                        <p className="font-medium text-slate-800">{r.product_name}</p>
                        <p className="text-xs text-slate-500">{r.category} · {r.order_id}</p>
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap">{fmtDate(r.delivery_date)}</td>
                      <td className="px-4 py-2 whitespace-nowrap">{fmtDate(r.return_date)}</td>
                      <td className={`px-4 py-2 text-right tabular-nums ${r.days_to_return < 2 ? 'font-semibold text-risk-medium' : ''}`}>{r.days_to_return}</td>
                      <td className="px-4 py-2">
                        <p>{humanize(r.reason_code)}</p>
                        {r.reason_text && <p className="text-xs text-slate-500">“{r.reason_text}”</p>}
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex flex-wrap gap-1">
                          {r.mismatch_flag && <Tag tone="red"><ShieldAlert className="h-3 w-3" />Mismatch</Tag>}
                          {r.is_vague && <Tag tone="amber">Vague</Tag>}
                          {r.days_to_return < 2 && <Tag tone="amber">Fast return</Tag>}
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">{fmtMoney(r.refund_amount)}</td>
                      <td className="px-4 py-2 text-xs">{humanize(r.return_status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader title="Order history" subtitle={orders.data ? `${orders.data.total} orders` : undefined} />
        {orders.error ? (
          <ErrorState message={orders.error} onRetry={orders.reload} />
        ) : orders.loading ? (
          <TableSkeleton rows={5} cols={6} />
        ) : !orders.data?.items.length ? (
          <EmptyState title="No orders" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 text-left text-xs font-medium text-slate-500">
                  <th className="px-4 py-2">Order</th>
                  <th className="px-4 py-2">Product</th>
                  <th className="px-4 py-2">Ordered</th>
                  <th className="px-4 py-2">Delivered</th>
                  <th className="px-4 py-2 text-right">Amount</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Rating</th>
                  <th className="px-4 py-2">Returned</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {orders.data.items.map((o) => (
                  <tr key={o.order_id}>
                    <td className="px-4 py-2 font-mono text-xs text-slate-600">{o.order_id}</td>
                    <td className="px-4 py-2">
                      {o.product_name} <span className="text-xs text-slate-500">· {o.category}</span>
                    </td>
                    <td className="px-4 py-2 whitespace-nowrap">{fmtDate(o.order_date)}</td>
                    <td className="px-4 py-2 whitespace-nowrap">{fmtDate(o.delivery_date)}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{fmtMoney(o.order_amount)}</td>
                    <td className="px-4 py-2 text-xs">{humanize(o.order_status)}</td>
                    <td className="px-4 py-2">{o.customer_rating ? `${o.customer_rating}★` : '—'}</td>
                    <td className="px-4 py-2">{o.returned ? <Tag>Returned</Tag> : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
