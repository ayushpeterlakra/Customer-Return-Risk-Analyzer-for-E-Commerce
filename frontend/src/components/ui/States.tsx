import { AlertTriangle, Inbox, RefreshCw } from 'lucide-react'
import { Button } from './Button'

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate-100 ${className}`} />
}

export function TableSkeleton({ rows = 8, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-3 p-5" data-testid="table-skeleton">
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="flex gap-4">
          {Array.from({ length: cols }, (_, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

export function EmptyState({ title, message }: { title: string; message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <Inbox className="h-8 w-8 text-slate-300" aria-hidden />
      <p className="mt-3 text-sm font-medium text-slate-700">{title}</p>
      {message && <p className="mt-1 max-w-sm text-xs text-slate-500">{message}</p>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center px-6 py-10 text-center">
      <AlertTriangle className="h-8 w-8 text-red-400" aria-hidden />
      <p className="mt-3 text-sm font-medium text-slate-800">Could not load data</p>
      <p className="mt-1 max-w-md text-xs text-slate-500">{message}</p>
      {onRetry && (
        <Button className="mt-4" onClick={onRetry} icon={<RefreshCw className="h-4 w-4" aria-hidden />}>
          Try again
        </Button>
      )}
    </div>
  )
}
