import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from './Button'

interface Props {
  page: number
  pages: number
  total: number
  pageSize: number
  onChange: (page: number) => void
}

export function Pagination({ page, pages, total, pageSize, onChange }: Props) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-5 py-3 text-sm">
      <p className="text-slate-500">
        Showing <span className="font-medium text-slate-700">{from}</span>–<span className="font-medium text-slate-700">{to}</span> of{' '}
        <span className="font-medium text-slate-700">{total}</span>
      </p>
      <div className="flex items-center gap-2">
        <Button aria-label="Previous page" disabled={page <= 1} onClick={() => onChange(page - 1)} icon={<ChevronLeft className="h-4 w-4" />} />
        <span className="tabular-nums text-slate-600">
          Page {page} of {pages}
        </span>
        <Button aria-label="Next page" disabled={page >= pages} onClick={() => onChange(page + 1)} icon={<ChevronRight className="h-4 w-4" />} />
      </div>
    </div>
  )
}
