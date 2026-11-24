import { Download } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/endpoints'
import { ChangeReviewModal } from '../components/ReviewPanel'
import { ReviewBadge, ScoreBar } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Select } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { Pagination } from '../components/ui/Pagination'
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/States'
import { StatCard } from '../components/ui/StatCard'
import { useApi } from '../hooks/useApi'
import { REVIEW_LABEL, REVIEW_STATUSES, fmtDateTime } from '../lib/format'
import type { HighRiskItem, ReviewStatus } from '../types/api'
import { AlertOctagon, Clock, Search, ShieldCheck } from 'lucide-react'

export function MonitoringPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<ReviewStatus | ''>('')
  const list = useApi(() => api.highRisk(page, status || undefined), [page, status])
  const all = useApi(() => api.highRisk(1), [])
  const pending = useApi(() => api.highRisk(1, 'PENDING_REVIEW'), [])
  const investigating = useApi(() => api.highRisk(1, 'UNDER_INVESTIGATION'), [])
  const [editing, setEditing] = useState<HighRiskItem | null>(null)

  const refreshAll = () => {
    list.reload()
    all.reload()
    pending.reload()
    investigating.reload()
  }

  return (
    <>
      <PageHeader
        title="Risk monitoring"
        description="Customers with a HIGH score are queued for manual review. Investigate the history before acting; a score is not proof of fraud."
        actions={
          <a href={api.exportUrl('HIGH')} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
            <Download className="h-4 w-4" aria-hidden /> Export high-risk CSV
          </a>
        }
      />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="High-risk customers" value={String(all.data?.total ?? '—')} icon={AlertOctagon} tone="high" loading={all.loading} />
        <StatCard label="Pending review" value={String(pending.data?.total ?? '—')} icon={Clock} tone="medium" loading={pending.loading} />
        <StatCard label="Under investigation" value={String(investigating.data?.total ?? '—')} icon={Search} loading={investigating.loading} />
      </div>
      <Card>
        <div className="flex flex-wrap items-end gap-3 border-b border-slate-100 p-4">
          <Select
            label="Review status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as ReviewStatus | '')
              setPage(1)
            }}
          >
            <option value="">All statuses</option>
            {REVIEW_STATUSES.map((s) => (
              <option key={s} value={s}>
                {REVIEW_LABEL[s]}
              </option>
            ))}
          </Select>
        </div>
        {list.error ? (
          <ErrorState message={list.error} onRetry={list.reload} />
        ) : list.loading && !list.data ? (
          <TableSkeleton rows={6} cols={6} />
        ) : !list.data?.items.length ? (
          <EmptyState title="Nothing in this queue" message={status ? 'No high-risk customers have this review status.' : 'No customers are currently high risk.'} />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[880px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/60 text-left text-xs font-medium text-slate-500">
                    <th className="px-4 py-2.5">Customer</th>
                    <th className="px-4 py-2.5">Score</th>
                    <th className="px-4 py-2.5">Major risk factors</th>
                    <th className="px-4 py-2.5">Review status</th>
                    <th className="px-4 py-2.5">Last review change</th>
                    <th className="px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {list.data.items.map((c) => (
                    <tr key={c.customer_id} className="align-top hover:bg-slate-50/70">
                      <td className="px-4 py-3">
                        <Link to={`/customers/${c.customer_id}`} className="font-medium text-slate-800 hover:text-primary">
                          {c.name}
                        </Link>
                        <p className="font-mono text-xs text-slate-500">{c.customer_id}</p>
                      </td>
                      <td className="px-4 py-3">
                        <ScoreBar score={c.risk_score} level={c.risk_level} />
                      </td>
                      <td className="px-4 py-3">
                        <ul className="space-y-0.5 text-xs text-slate-600">
                          {c.top_factors.map((f) => (
                            <li key={f.rule_id}>
                              {f.factor} <span className="font-medium text-slate-800">+{f.contribution}</span>
                            </li>
                          ))}
                        </ul>
                      </td>
                      <td className="px-4 py-3">
                        <ReviewBadge status={c.review_status} />
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">{fmtDateTime(c.review_updated_at)}</td>
                      <td className="px-4 py-3 text-right">
                        <Button onClick={() => setEditing(c)} icon={<ShieldCheck className="h-4 w-4" />}>
                          Update
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={list.data.page} pages={list.data.pages} total={list.data.total} pageSize={list.data.page_size} onChange={setPage} />
          </>
        )}
      </Card>
      {editing && (
        <ChangeReviewModal
          key={editing.customer_id}
          customerId={editing.customer_id}
          current={editing.review_status}
          open
          onClose={() => setEditing(null)}
          onSaved={refreshAll}
        />
      )}
    </>
  )
}
