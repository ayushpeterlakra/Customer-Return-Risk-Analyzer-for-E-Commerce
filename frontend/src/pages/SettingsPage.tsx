import { FileUp, RefreshCw, RotateCcw, Save } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/endpoints'
import { errorDetails, toErrorMessage } from '../api/client'
import { Button } from '../components/ui/Button'
import { Card, CardHeader } from '../components/ui/Card'
import { Input, Toggle } from '../components/ui/Field'
import { PageHeader } from '../components/ui/PageHeader'
import { ErrorState, Skeleton } from '../components/ui/States'
import { useApi } from '../hooks/useApi'
import { humanize } from '../lib/format'
import type { ScoringConfig } from '../types/api'

const GROUP_OF: Record<string, string> = {
  high_return_ratio: 'return_volume',
  very_high_return_ratio: 'return_volume',
  high_return_frequency: 'return_volume',
  vague_reasons: 'return_reasons',
  repeated_reason: 'return_reasons',
  mismatch_history: 'item_mismatch',
  short_return_window: 'return_timing',
  high_return_categories: 'behaviour',
  returns_after_high_rating: 'behaviour',
  rising_return_rate: 'behaviour',
}

type Feedback = { kind: 'ok' | 'error'; text: string; details?: string[] } | null

function RulesEditor({ initial, source, onSaved }: { initial: ScoringConfig; source: string; onSaved: () => void }) {
  const [cfg, setCfg] = useState<ScoringConfig>(initial)
  const [by, setBy] = useState('')
  const [busy, setBusy] = useState(false)
  const [feedback, setFeedback] = useState<Feedback>(null)
  const dirty = JSON.stringify(cfg) !== JSON.stringify(initial)

  const setRule = (rule: string, key: string, value: number | boolean) =>
    setCfg((c) => ({ ...c, rules: { ...c.rules, [rule]: { ...c.rules[rule], [key]: value } } }))

  const run = async (action: () => Promise<unknown>, ok: string) => {
    setBusy(true)
    setFeedback(null)
    try {
      await action()
      setFeedback({ kind: 'ok', text: ok })
      onSaved()
    } catch (err) {
      const details = errorDetails(err)
      setFeedback({
        kind: 'error',
        text: toErrorMessage(err),
        details: Array.isArray(details) ? details.map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).slice(2).join('.')}: ${d.msg}`) : undefined,
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader
        title="Risk scoring rules"
        subtitle={`Active version ${initial.version} (from ${source}). Saving creates a new version and rescores every customer.`}
        actions={
          <>
            <Button icon={<RotateCcw className="h-4 w-4" />} disabled={busy} onClick={() => run(api.resetRules, 'Default rules restored and all customers rescored.')}>
              Restore defaults
            </Button>
          </>
        }
      />
      <div className="grid gap-6 p-5 lg:grid-cols-3">
        <div className="space-y-3">
          <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">Risk level thresholds</p>
          <Input label="Low risk up to" type="number" min={0} max={99} value={cfg.levels.low_max} onChange={(e) => setCfg({ ...cfg, levels: { ...cfg.levels, low_max: Number(e.target.value) } })} />
          <Input label="Medium risk up to" type="number" min={1} max={99} value={cfg.levels.medium_max} onChange={(e) => setCfg({ ...cfg, levels: { ...cfg.levels, medium_max: Number(e.target.value) } })} />
          <p className="pt-2 text-xs font-medium tracking-wide text-slate-500 uppercase">Group caps (max points)</p>
          {Object.entries(cfg.group_caps).map(([g, v]) => (
            <Input key={g} label={humanize(g)} type="number" min={0} max={100} value={v} onChange={(e) => setCfg({ ...cfg, group_caps: { ...cfg.group_caps, [g]: Number(e.target.value) } })} />
          ))}
        </div>
        <div className="space-y-3 lg:col-span-2">
          <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">Rules</p>
          {Object.entries(cfg.rules).map(([name, rule]) => (
            <div key={name} className={`rounded-lg border p-3 ${rule.enabled ? 'border-slate-200' : 'border-dashed border-slate-200 opacity-60'}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Toggle label={humanize(name)} checked={rule.enabled} onChange={(v) => setRule(name, 'enabled', v)} />
                <span className="text-xs text-slate-400">{humanize(GROUP_OF[name] ?? '')}</span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {Object.entries(rule)
                  .filter(([k]) => k !== 'enabled')
                  .map(([k, v]) => (
                    <Input key={k} label={humanize(k)} type="number" step={Number.isInteger(v) ? 1 : 0.01} value={Number(v)} disabled={!rule.enabled} onChange={(e) => setRule(name, k, Number(e.target.value))} />
                  ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="flex flex-wrap items-end justify-between gap-3 border-t border-slate-100 px-5 py-4">
        <div className="w-64">
          <Input label="Your name (recorded with the version)" value={by} maxLength={120} onChange={(e) => setBy(e.target.value)} />
        </div>
        <div className="flex gap-2">
          <Button disabled={!dirty || busy} onClick={() => setCfg(initial)}>
            Discard changes
          </Button>
          <Button variant="primary" icon={<Save className="h-4 w-4" />} disabled={!dirty || busy || !by.trim()} onClick={() => run(() => api.saveRules(cfg, by.trim()), 'Rules saved and all customers rescored.')}>
            {busy ? 'Saving…' : 'Save and rescore'}
          </Button>
        </div>
      </div>
      {feedback && (
        <div role={feedback.kind === 'error' ? 'alert' : 'status'} className={`mx-5 mb-5 rounded-lg p-3 text-sm ${feedback.kind === 'ok' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-700'}`}>
          {feedback.text}
          {feedback.details && (
            <ul className="mt-1 list-disc pl-5 text-xs">
              {feedback.details.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  )
}

function DataTools() {
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState<'import' | 'rescore' | null>(null)
  const [feedback, setFeedback] = useState<Feedback>(null)

  const doImport = async () => {
    if (!file) return
    setBusy('import')
    setFeedback(null)
    try {
      const r = await api.importCsv(file)
      const i = r.imported
      setFeedback({ kind: 'ok', text: `Imported ${i.orders} orders, ${i.returns} returns, ${i.customers} new customers, ${i.products} new products. Rescored ${r.rescored.assessed} customers.` })
    } catch (err) {
      const details = errorDetails(err)
      setFeedback({
        kind: 'error',
        text: toErrorMessage(err),
        details: Array.isArray(details) ? details.slice(0, 20).map((d: { line?: number; field?: string; message?: string }) => `Line ${d.line}, ${d.field}: ${d.message}`) : undefined,
      })
    } finally {
      setBusy(null)
    }
  }

  const rescore = async () => {
    setBusy('rescore')
    setFeedback(null)
    try {
      const r = await api.assessAll()
      setFeedback({ kind: 'ok', text: `Rescored ${r.assessed} customers in ${r.duration_ms} ms: ${r.HIGH} high, ${r.MEDIUM} medium, ${r.LOW} low.` })
    } catch (err) {
      setFeedback({ kind: 'error', text: toErrorMessage(err) })
    } finally {
      setBusy(null)
    }
  }

  return (
    <Card>
      <CardHeader title="Data" subtitle="Import orders and returns, or rescore everyone with the current rules" />
      <div className="space-y-4 p-5 text-sm">
        <div className="flex flex-wrap items-center gap-3">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-slate-300 px-3 py-2 text-slate-600 hover:bg-slate-50">
            <FileUp className="h-4 w-4" aria-hidden />
            {file ? file.name : 'Choose CSV file'}
            <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <Button variant="primary" disabled={!file || busy !== null} onClick={doImport}>
            {busy === 'import' ? 'Importing…' : 'Import'}
          </Button>
          <a href={api.templateUrl()} className="text-xs font-medium text-primary hover:underline">
            Download template
          </a>
        </div>
        <p className="text-xs text-slate-500">Imports are all-or-nothing: if any row is invalid, nothing is saved and every problem is listed with its line number.</p>
        <div className="border-t border-slate-100 pt-4">
          <Button icon={<RefreshCw className={`h-4 w-4 ${busy === 'rescore' ? 'animate-spin' : ''}`} />} disabled={busy !== null} onClick={rescore}>
            Rescore all customers
          </Button>
        </div>
        {feedback && (
          <div role={feedback.kind === 'error' ? 'alert' : 'status'} className={`rounded-lg p-3 ${feedback.kind === 'ok' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-700'}`}>
            {feedback.text}
            {feedback.details && (
              <ul className="mt-1 list-disc pl-5 text-xs">
                {feedback.details.map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}

export function SettingsPage() {
  const rules = useApi(() => api.rules(), [])
  return (
    <>
      <PageHeader title="Settings" description="Tune the scoring rules and manage data. Every rule change is versioned, and each assessment records the version it used." />
      <div className="space-y-6">
        {rules.error ? (
          <Card>
            <ErrorState message={rules.error} onRetry={rules.reload} />
          </Card>
        ) : !rules.data ? (
          <Skeleton className="h-96" />
        ) : (
          <RulesEditor key={rules.data.config.version} initial={rules.data.config} source={rules.data.source} onSaved={rules.reload} />
        )}
        <DataTools />
        <Card>
          <CardHeader title="Email alerts" subtitle="Optional notice when a customer newly becomes high risk" />
          <p className="p-5 text-sm text-slate-600">
            {rules.data?.email_alerts_enabled
              ? 'Enabled. Alerts contain the customer ID and score only.'
              : 'Disabled. Set SMTP_HOST, ALERT_EMAIL_FROM and ALERT_EMAIL_TO in backend/.env and restart the API to enable them.'}
          </p>
        </Card>
      </div>
    </>
  )
}
