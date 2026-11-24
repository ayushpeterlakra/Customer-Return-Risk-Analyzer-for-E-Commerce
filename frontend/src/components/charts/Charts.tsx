import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { CategoryReturns, HistoryPoint, LevelCount, RatioBucket, ReasonCount, TrendPoint } from '../../types/api'
import { CHART_PRIMARY, CHART_SECONDARY, RISK_COLORS, RISK_LABEL, fmtDate, humanize } from '../../lib/format'

const axis = { fontSize: 12, fill: '#64748b' }
const grid = <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
const tooltipStyle = { borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12 }

export function CategoryBarChart({ data }: { data: CategoryReturns[] }) {
  const rows = data.map((d) => ({ ...d, rate: +(d.return_rate * 100).toFixed(1) }))
  return (
    <ResponsiveContainer>
      <BarChart data={rows} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
        {grid}
        <XAxis dataKey="category" tick={axis} interval={0} angle={-25} textAnchor="end" height={60} />
        <YAxis tick={axis} allowDecimals={false} />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(value, name) => [value, name]}
          labelFormatter={(label, payload) => {
            const p = payload?.[0]?.payload as (typeof rows)[number] | undefined
            return p ? `${label}: ${p.rate}% of ${p.orders} delivered orders returned` : String(label)
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="returns" name="Returns" fill={CHART_PRIMARY} radius={[4, 4, 0, 0]} />
        <Bar dataKey="mismatches" name="Mismatched items" fill="#f59e0b" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function RiskDonut({ data }: { data: LevelCount[] }) {
  const order: LevelCount['risk_level'][] = ['LOW', 'MEDIUM', 'HIGH']
  const rows = order.map((lvl) => data.find((d) => d.risk_level === lvl) ?? { risk_level: lvl, count: 0, percentage: 0 })
  const total = rows.reduce((s, r) => s + r.count, 0)
  return (
    <ResponsiveContainer>
      <PieChart>
        <Pie data={rows} dataKey="count" nameKey="risk_level" innerRadius="58%" outerRadius="82%" paddingAngle={2} stroke="none">
          {rows.map((r) => (
            <Cell key={r.risk_level} fill={RISK_COLORS[r.risk_level]} />
          ))}
        </Pie>
        <text x="50%" y="46%" textAnchor="middle" className="fill-slate-900 text-2xl font-semibold">
          {total}
        </text>
        <text x="50%" y="56%" textAnchor="middle" className="fill-slate-500 text-xs">
          customers
        </text>
        <Tooltip contentStyle={tooltipStyle} formatter={(v, _n, item) => [`${v} (${(item.payload as LevelCount).percentage}%)`, RISK_LABEL[(item.payload as LevelCount).risk_level]]} />
        <Legend wrapperStyle={{ fontSize: 12 }} formatter={(value: string) => `${RISK_LABEL[value as LevelCount['risk_level']]} risk`} />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function TrendChart({ data }: { data: TrendPoint[] }) {
  return (
    <ResponsiveContainer>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        {grid}
        <XAxis dataKey="period_start" tick={axis} tickFormatter={(v: string) => fmtDate(v).slice(0, 6)} minTickGap={24} />
        <YAxis tick={axis} allowDecimals={false} />
        <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => `Period starting ${fmtDate(String(v))}`} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="orders" name="Orders" stroke={CHART_SECONDARY} strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="returns" name="Returns" stroke={CHART_PRIMARY} strokeWidth={2.5} dot={false} />
        <Line type="monotone" dataKey="mismatches" name="Mismatches" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function RatioHistogram({ data }: { data: RatioBucket[] }) {
  return (
    <ResponsiveContainer>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
        {grid}
        <XAxis dataKey="bucket" tick={axis} interval={0} angle={-25} textAnchor="end" height={50} />
        <YAxis tick={axis} allowDecimals={false} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => [v, 'Customers']} labelFormatter={(l) => `Return ratio ${l}`} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="customers" name="Customers" fill={CHART_PRIMARY} radius={[4, 4, 0, 0]}>
          {data.map((b) => (
            <Cell key={b.bucket} fill={b.lower >= 0.4 ? RISK_COLORS.HIGH : b.lower >= 0.3 ? RISK_COLORS.MEDIUM : CHART_PRIMARY} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function ReasonsChart({ data }: { data: ReasonCount[] }) {
  const rows = data.map((d) => ({ ...d, label: humanize(d.reason_code), explained: d.count - d.vague }))
  return (
    <ResponsiveContainer>
      <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 16, left: 24, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
        <XAxis type="number" tick={axis} allowDecimals={false} />
        <YAxis type="category" dataKey="label" tick={axis} width={120} />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="explained" stackId="a" name="With explanation" fill={CHART_PRIMARY} />
        <Bar dataKey="vague" stackId="a" name="Vague (no explanation)" fill="#f59e0b" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function ScoreHistoryChart({ data, lowMax = 40, mediumMax = 70 }: { data: HistoryPoint[]; lowMax?: number; mediumMax?: number }) {
  const rows = data.map((d, i) => ({ ...d, n: i + 1 }))
  return (
    <ResponsiveContainer>
      <AreaChart data={rows} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
        {grid}
        <XAxis dataKey="assessed_at" tick={axis} tickFormatter={(v: string) => fmtDate(v).slice(0, 6)} minTickGap={24} />
        <YAxis domain={[0, 100]} tick={axis} />
        <ReferenceLine y={lowMax} stroke={RISK_COLORS.MEDIUM} strokeDasharray="4 4" />
        <ReferenceLine y={mediumMax} stroke={RISK_COLORS.HIGH} strokeDasharray="4 4" />
        <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => fmtDate(String(v))} formatter={(v, _n, item) => [`${v} (${(item.payload as HistoryPoint).config_version})`, 'Risk score']} />
        <Area type="stepAfter" dataKey="risk_score" name="Risk score" stroke={CHART_PRIMARY} fill={CHART_PRIMARY} fillOpacity={0.12} strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
