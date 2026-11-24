import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search, X } from 'lucide-react'
import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, type CustomerQuery } from '../api/endpoints'
import { RiskBadge, ReviewBadge, ScoreBar } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Select, Toggle } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { Pagination } from '../components/ui/Pagination'
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/States'
import { useApi } from '../hooks/useApi'
import { useDebounce } from '../hooks/useDebounce'
import { fmtDate, fmtPct } from '../lib/format'
import type { RiskLevel } from '../types/api'

const CATEGORIES = ['Fashion', 'Shoes', 'Electronics', 'Home & Kitchen', 'Beauty', 'Sports', 'Toys', 'Books']
const PAGE_SIZE = 20

type SortKey = 'customer_id' | 'name' | 'total_orders' | 'total_returns' | 'return_ratio' | 'risk_score' | 'last_return_date'

const COLUMNS: { key: SortKey | null; label: string; className?: string }[] = [
  { key: 'customer_id', label: 'Customer ID' },
  { key: 'name', label: 'Name' },
  { key: 'total_orders', label: 'Orders', className: 'text-right' },
  { key: 'total_returns', label: 'Returns', className: 'text-right' },
  { key: 'return_ratio', label: 'Return %', className: 'text-right' },
  { key: 'risk_score', label: 'Risk score' },
  { key: null, label: 'Risk level' },
  { key: 'last_return_date', label: 'Last return' },
  { key: null, label: 'Review' },
  { key: null, label: '' },
]

export function CustomersPage() {
  // Filters live in the URL so they survive reloads and the back button.
  const [params, setParams] = useSearchParams()
  const search = params.get('search') ?? ''
  const debounced = useDebounce(search)
  const query: CustomerQuery = useMemo(
    () => ({
      page: Number(params.get('page') ?? 1),
      page_size: PAGE_SIZE,
      search: debounced || undefined,
      risk_level: (params.get('risk_level') as RiskLevel) || undefined,
      min_score: params.get('high_score') ? 71 : undefined,
      min_return_ratio: params.get('high_ratio') ? 0.3 : undefined,
      category: params.get('category') || undefined,
      sort: params.get('sort') ?? 'risk_score',
      order: (params.get('order') as 'asc' | 'desc') ?? 'desc',
    }),
    [params, debounced],
  )
  const { data, error, loading, reload } = useApi(() => api.customers(query), [JSON.stringify(query)])

  // Functional update so quick successive changes never overwrite each other.
  const update = (changes: Record<string, string | null>, resetPage = true) => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        for (const [k, v] of Object.entries(changes)) {
          if (v) next.set(k, v)
          else next.delete(k)
        }
        if (resetPage) next.delete('page')
        return next
      },
      { replace: true },
    )
  }

  const toggleSort = (key: SortKey) => {
    if (query.sort === key) update({ order: query.order === 'desc' ? 'asc' : 'desc' }, false)
    else update({ sort: key, order: key === 'name' || key === 'customer_id' ? 'asc' : 'desc' }, false)
  }

  const activeFilters = ['search', 'risk_level', 'high_score', 'high_ratio', 'category'].some((k) => params.get(k))
  const exportHref = api.exportUrl(query.risk_level, query.min_score)

  return (
    <>
      <PageHeader
        title="Customers"
        description="Search, filter and sort every customer by return behaviour and current risk score."
        actions={
          <a href={exportHref} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
            <Download className="h-4 w-4" aria-hidden />
            Export CSV{query.risk_level ? ` (${query.risk_level.toLowerCase()})` : ' (all scored)'}
          </a>
        }
      />
      <Card>
        <div className="flex flex-wrap items-end gap-3 border-b border-slate-100 p-4">
          <label className="relative flex-1 basis-60">
            <span className="sr-only">Search customers</span>
            <Search className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-slate-400" aria-hidden />
            <input
              value={search}
              onChange={(e) => update({ search: e.target.value || null })}
              placeholder="Search by customer ID or name"
              className="w-full rounded-lg border border-slate-200 py-1.5 pr-3 pl-9 text-sm focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none"
            />
          </label>
          <Select label="Risk level" value={params.get('risk_level') ?? ''} onChange={(e) => update({ risk_level: e.target.value || null })}>
            <option value="">All levels</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </Select>
          <Select label="Bought in category" value={params.get('category') ?? ''} onChange={(e) => update({ category: e.target.value || null })}>
            <option value="">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </Select>
          <div className="flex flex-col gap-2 pb-0.5">
            <Toggle label="Return ratio above 30%" checked={!!params.get('high_ratio')} onChange={(v) => update({ high_ratio: v ? '1' : null })} />
            <Toggle label="Risk score above 70" checked={!!params.get('high_score')} onChange={(v) => update({ high_score: v ? '1' : null })} />
          </div>
          {activeFilters && (
            <Button variant="ghost" icon={<X className="h-4 w-4" />} onClick={() => setParams(new URLSearchParams(), { replace: true })}>
              Clear filters
            </Button>
          )}
        </div>

        {error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : loading && !data ? (
          <TableSkeleton rows={10} cols={8} />
        ) : !data?.items.length ? (
          <EmptyState title="No customers match these filters" message="Clear a filter or change the search text." />
        ) : (
          <>
            <div className={`overflow-x-auto transition-opacity ${loading ? 'opacity-60' : ''}`}>
              <table className="w-full min-w-[900px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/60 text-left text-xs font-medium text-slate-500">
                    {COLUMNS.map((col) => (
                      <th key={col.label || 'action'} className={`px-4 py-2.5 ${col.className ?? ''}`} aria-sort={col.key && query.sort === col.key ? (query.order === 'asc' ? 'ascending' : 'descending') : undefined}>
                        {col.key ? (
                          <button type="button" onClick={() => toggleSort(col.key!)} className="inline-flex items-center gap-1 hover:text-slate-800">
                            {col.label}
                            {query.sort === col.key ? (
                              query.order === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                            ) : (
                              <ArrowUpDown className="h-3 w-3 opacity-40" />
                            )}
                          </button>
                        ) : (
                          col.label
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.map((c) => (
                    <tr key={c.customer_id} className="hover:bg-slate-50/70">
                      <td className="px-4 py-2.5 font-mono text-xs text-slate-600">{c.customer_id}</td>
                      <td className="px-4 py-2.5 font-medium text-slate-800">{c.name}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{c.total_orders}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">{c.total_returns}</td>
                      <td className={`px-4 py-2.5 text-right tabular-nums ${c.return_percentage > 40 ? 'font-semibold text-risk-high' : ''}`}>{fmtPct(c.return_percentage)}</td>
                      <td className="px-4 py-2.5">
                        <ScoreBar score={c.risk_score} level={c.risk_level} />
                      </td>
                      <td className="px-4 py-2.5">
                        <RiskBadge level={c.risk_level} />
                      </td>
                      <td className="px-4 py-2.5 whitespace-nowrap text-slate-600">{fmtDate(c.last_return_date)}</td>
                      <td className="px-4 py-2.5">
                        <ReviewBadge status={c.review_status} />
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <Link to={`/customers/${c.customer_id}`} className="text-xs font-medium whitespace-nowrap text-primary hover:underline">
                          View profile
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} onChange={(p) => update({ page: String(p) }, false)} />
          </>
        )}
      </Card>
    </>
  )
}
