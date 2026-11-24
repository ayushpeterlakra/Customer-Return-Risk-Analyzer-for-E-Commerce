import type { DateRange } from '../../types/api'
import { Button } from './Button'
import { Input } from './Field'

const PRESETS = [
  { label: '30 days', days: 30 },
  { label: '90 days', days: 90 },
  { label: '12 months', days: 365 },
]

const iso = (d: Date) => d.toISOString().slice(0, 10)

export function DateRangeFilter({ value, onChange }: { value: DateRange; onChange: (r: DateRange) => void }) {
  const invalid = Boolean(value.date_from && value.date_to && value.date_from > value.date_to)
  return (
    <div className="flex flex-wrap items-end gap-2">
      <Input label="From" type="date" value={value.date_from ?? ''} max={value.date_to} onChange={(e) => onChange({ ...value, date_from: e.target.value || undefined })} />
      <Input label="To" type="date" value={value.date_to ?? ''} min={value.date_from} onChange={(e) => onChange({ ...value, date_to: e.target.value || undefined })} />
      <div className="flex gap-1">
        {PRESETS.map((p) => (
          <Button
            key={p.days}
            variant="ghost"
            onClick={() => {
              const to = new Date()
              const from = new Date(to.getTime() - p.days * 86_400_000)
              onChange({ date_from: iso(from), date_to: iso(to) })
            }}
          >
            {p.label}
          </Button>
        ))}
        <Button variant="ghost" disabled={!value.date_from && !value.date_to} onClick={() => onChange({})}>
          All time
        </Button>
      </div>
      {invalid && <p className="w-full text-xs text-red-600">The start date must be on or before the end date.</p>}
    </div>
  )
}
