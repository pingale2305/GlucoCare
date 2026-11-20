import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, LabelList, Legend } from 'recharts'
import { fmtDate } from '../utils/format'

export const COLORS = { teal: '#0d9488', sky: '#0ea5e9', rose: '#e11d48', amber: '#f59e0b', green: '#10b981', violet: '#8b5cf6' }
const tsFmt = (t) => new Date(t).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: '2-digit' })
const tip = { contentStyle: { borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 } }

export function NoData({ children = 'Not enough data to chart.' }) {
  return <div className="grid h-40 place-items-center rounded-xl border border-dashed border-slate-200 text-center text-xs text-slate-400"><span className="max-w-xs px-4">{children}</span></div>
}

/** HbA1c over time with a target line (green below, red above). */
export function HbA1cChart({ series = [], target = 7, height = 260 }) {
  const data = useMemo(() => series.map((s) => ({ t: new Date(s.date).getTime(), value: s.value })), [series])
  if (data.length < 2) return <NoData>{data.length === 1 ? `Only one HbA1c result (${data[0].value}% on ${fmtDate(series[0].date)}).` : 'No HbA1c results recorded.'}</NoData>
  const hi = Math.max(10, ...data.map((d) => d.value + 0.8)); const lo = Math.min(4, ...data.map((d) => d.value - 0.5))
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 22, right: 28, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
        <ReferenceArea y1={target} y2={hi} fill="#f43f5e" fillOpacity={0.08} />
        <ReferenceArea y1={lo} y2={target} fill="#10b981" fillOpacity={0.09} />
        <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={tsFmt} tick={{ fill: '#64748b' }} />
        <YAxis domain={[Math.floor(lo), Math.ceil(hi)]} tick={{ fill: '#64748b' }} />
        <ReferenceLine y={target} stroke={COLORS.sky} strokeWidth={2} label={{ value: `Target ${target}%`, position: 'insideTopRight', fontSize: 11, fill: COLORS.sky }} />
        <Tooltip {...tip} labelFormatter={tsFmt} formatter={(v) => [`${v}%`, 'HbA1c']} />
        <Line type="monotone" dataKey="value" stroke={COLORS.sky} strokeWidth={2.5} dot={{ r: 5, fill: '#fff', stroke: COLORS.sky, strokeWidth: 2 }}>
          <LabelList dataKey="value" position="top" fontSize={11} fill="#334155" />
        </Line>
      </LineChart>
    </ResponsiveContainer>
  )
}

/** One or more lab series on the same date axis. lines = [{key, name, color, data:[{date,value}]}] */
export function LinesChart({ lines = [], unit = '', refs = [], height = 260 }) {
  const rows = useMemo(() => {
    const m = {}
    lines.forEach((l) => l.data.forEach((p) => { const t = new Date(p.date).getTime(); (m[t] ||= { t })[l.key] = p.value }))
    return Object.values(m).sort((a, b) => a.t - b.t)
  }, [lines])
  const points = Math.max(0, ...lines.map((l) => l.data.length))
  if (points < 2) return <NoData>{points === 1 ? 'Only one result recorded so far.' : 'No results recorded.'}</NoData>
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={rows} margin={{ top: 10, right: 16, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
        <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={tsFmt} tick={{ fill: '#64748b' }} />
        <YAxis domain={['auto', 'auto']} tick={{ fill: '#64748b' }} />
        {refs.map((r) => <ReferenceLine key={r.label} y={r.y} stroke={r.color || '#94a3b8'} strokeDasharray="4 4" label={{ value: r.label, position: 'insideTopRight', fontSize: 10, fill: r.color || '#64748b' }} />)}
        <Tooltip {...tip} labelFormatter={tsFmt} formatter={(v, n) => [`${v} ${unit}`, n]} />
        {lines.length > 1 && <Legend />}
        {lines.map((l) => <Line key={l.key} name={l.name} type="monotone" dataKey={l.key} stroke={l.color} strokeWidth={2.5} connectNulls dot={{ r: 4, fill: '#fff', stroke: l.color, strokeWidth: 2 }} />)}
      </LineChart>
    </ResponsiveContainer>
  )
}

/** Entered glucose readings (mg/dL) with the 70-180 band shaded. readings: [{measured_at, value_mg_dl, context}] */
export function GlucoseChart({ readings = [], height = 260 }) {
  const data = useMemo(() => readings.map((r) => ({ t: new Date(r.measured_at).getTime(), value: r.value_mg_dl, context: r.context }))
    .sort((a, b) => a.t - b.t), [readings])
  if (data.length < 2) return <NoData>{data.length ? 'Add one more reading to see the chart.' : 'No readings yet.'}</NoData>
  const hi = Math.max(200, ...data.map((d) => d.value + 20)); const lo = Math.min(60, ...data.map((d) => d.value - 10))
  const dt = (t) => new Date(t).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
        <ReferenceArea y1={70} y2={180} fill="#10b981" fillOpacity={0.09} />
        <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={tsFmt} tick={{ fill: '#64748b' }} />
        <YAxis domain={[Math.floor(lo / 10) * 10, Math.ceil(hi / 10) * 10]} tick={{ fill: '#64748b' }} />
        <Tooltip {...tip} labelFormatter={dt} formatter={(v) => [`${v} mg/dL`, 'Glucose']} />
        <Line type="monotone" dataKey="value" stroke={COLORS.teal} strokeWidth={2.5} dot={{ r: 3.5, fill: '#fff', stroke: COLORS.teal, strokeWidth: 2 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

/** Daily steps. steps: [{entry_date, steps}] */
export function StepsChart({ steps = [], height = 220 }) {
  const data = useMemo(() => steps.map((s) => ({ t: s.entry_date, steps: s.steps })).sort((a, b) => (a.t < b.t ? -1 : 1)).slice(-30), [steps])
  if (!data.length) return <NoData>No walking records yet.</NoData>
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 10, right: 16, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
        <XAxis dataKey="t" tickFormatter={(d) => fmtDate(d).slice(0, 6)} tick={{ fill: '#64748b' }} />
        <YAxis tick={{ fill: '#64748b' }} />
        <Tooltip {...tip} labelFormatter={fmtDate} formatter={(v) => [Number(v).toLocaleString(), 'Steps']} />
        <Bar dataKey="steps" fill={COLORS.teal} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
