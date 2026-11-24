import type { ReactNode } from 'react'
import { Card, CardHeader } from '../ui/Card'
import { EmptyState, ErrorState, Skeleton } from '../ui/States'

interface Props {
  title: string
  subtitle?: string
  loading: boolean
  error: string | null
  empty: boolean
  onRetry: () => void
  actions?: ReactNode
  height?: number
  children: ReactNode
}

/** Card wrapper giving every chart the same loading, empty and error states. */
export function ChartFrame({ title, subtitle, loading, error, empty, onRetry, actions, height = 280, children }: Props) {
  return (
    <Card>
      <CardHeader title={title} subtitle={subtitle} actions={actions} />
      <div className="p-4" style={{ minHeight: height }}>
        {error ? (
          <ErrorState message={error} onRetry={onRetry} />
        ) : loading ? (
          <Skeleton className="h-[260px] w-full" />
        ) : empty ? (
          <EmptyState title="No data for this selection" message="Try a wider date range or different filters." />
        ) : (
          <div style={{ height }}>{children}</div>
        )}
      </div>
    </Card>
  )
}
