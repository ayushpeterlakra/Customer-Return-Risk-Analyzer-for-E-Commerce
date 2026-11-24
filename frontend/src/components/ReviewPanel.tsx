import { History } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/endpoints'
import { toErrorMessage } from '../api/client'
import { useApi } from '../hooks/useApi'
import { REVIEW_LABEL, REVIEW_STATUSES, fmtDateTime } from '../lib/format'
import type { ReviewStatus } from '../types/api'
import { ReviewBadge } from './ui/Badge'
import { Button } from './ui/Button'
import { Card, CardHeader } from './ui/Card'
import { Input, Select } from './ui/Field'
import { Modal } from './ui/Modal'
import { EmptyState, ErrorState, TableSkeleton } from './ui/States'

const REVIEWER_KEY = 'rra.reviewer'

function readReviewer(): string {
  try {
    return localStorage.getItem(REVIEWER_KEY) ?? ''
  } catch {
    return ''
  }
}

export function ChangeReviewModal({
  customerId,
  current,
  open,
  onClose,
  onSaved,
}: {
  customerId: string
  current: ReviewStatus | null
  open: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const [status, setStatus] = useState<ReviewStatus>(current === 'PENDING_REVIEW' ? 'UNDER_INVESTIGATION' : 'PENDING_REVIEW')
  const [notes, setNotes] = useState('')
  const [reviewer, setReviewer] = useState(readReviewer)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      await api.updateReview(customerId, { review_status: status, review_notes: notes || undefined, updated_by: reviewer.trim() })
      try {
        localStorage.setItem(REVIEWER_KEY, reviewer.trim())
      } catch {
        /* storage unavailable: remembering the name is optional */
      }
      setNotes('')
      onSaved()
      onClose()
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={`Update review for ${customerId}`}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={save} disabled={saving || !reviewer.trim() || status === current}>
            {saving ? 'Saving…' : 'Save status'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          Current status: <ReviewBadge status={current} />
        </p>
        <Select label="New status" value={status} onChange={(e) => setStatus(e.target.value as ReviewStatus)}>
          {REVIEW_STATUSES.map((s) => (
            <option key={s} value={s} disabled={s === current}>
              {REVIEW_LABEL[s]}
              {s === current ? ' (current)' : ''}
            </option>
          ))}
        </Select>
        <Input label="Your name (recorded in the audit trail)" value={reviewer} maxLength={120} onChange={(e) => setReviewer(e.target.value)} placeholder="e.g. Priya (Returns team)" />
        <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
          Notes
          <textarea
            value={notes}
            maxLength={2000}
            rows={3}
            onChange={(e) => setNotes(e.target.value)}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none"
            placeholder="What did you check, and what did you find?"
          />
        </label>
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 p-2 text-sm text-red-700">
            {error}
          </p>
        )}
      </div>
    </Modal>
  )
}

export function ReviewPanel({ customerId, current, onChanged }: { customerId: string; current: ReviewStatus | null; onChanged: () => void }) {
  const trail = useApi(() => api.reviewTrail(customerId), [customerId])
  const [open, setOpen] = useState(false)
  return (
    <Card>
      <CardHeader
        title="Manual review"
        subtitle="Every change is kept in the audit trail"
        actions={
          <Button variant="primary" onClick={() => setOpen(true)}>
            Change status
          </Button>
        }
      />
      <div className="px-5 pt-4 text-sm text-slate-600">
        Current status: <ReviewBadge status={current} />
      </div>
      <div className="px-5 pt-4 pb-1 text-xs font-medium tracking-wide text-slate-500 uppercase">
        <History className="mr-1 inline h-3.5 w-3.5" aria-hidden />
        Audit trail
      </div>
      {trail.error ? (
        <ErrorState message={trail.error} onRetry={trail.reload} />
      ) : trail.loading ? (
        <TableSkeleton rows={3} cols={2} />
      ) : !trail.data?.length ? (
        <EmptyState title="No review activity yet" />
      ) : (
        <ol className="space-y-3 px-5 py-3">
          {trail.data.map((r) => (
            <li key={r.id} className="border-l-2 border-slate-200 pl-3">
              <p className="text-sm text-slate-800">
                {r.previous_status ? `${REVIEW_LABEL[r.previous_status]} → ` : ''}
                <span className="font-medium">{REVIEW_LABEL[r.review_status]}</span>
              </p>
              <p className="text-xs text-slate-500">
                {r.updated_by} · {fmtDateTime(r.updated_at)}
              </p>
              {r.review_notes && <p className="mt-1 text-xs text-slate-600">{r.review_notes}</p>}
            </li>
          ))}
        </ol>
      )}
      <ChangeReviewModal
        key={String(open)}
        customerId={customerId}
        current={current}
        open={open}
        onClose={() => setOpen(false)}
        onSaved={() => {
          trail.reload()
          onChanged()
        }}
      />
    </Card>
  )
}
