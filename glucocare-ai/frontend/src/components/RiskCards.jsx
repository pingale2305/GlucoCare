import { Activity, Droplets, HeartPulse } from 'lucide-react'
import { fmtDate } from '../utils/format'

const TONE = {
  low: 'border-emerald-200 bg-emerald-50 text-emerald-800', moderate: 'border-amber-200 bg-amber-50 text-amber-800',
  high: 'border-rose-200 bg-rose-50 text-rose-800', insufficient: 'border-slate-200 bg-slate-50 text-slate-600',
}
const PARAM = { normal: 'text-slate-700', borderline: 'font-semibold text-amber-700', high: 'font-semibold text-rose-700', low: 'font-semibold text-rose-700', info: 'text-slate-500' }

function Card({ title, icon: Icon, r }) {
  return (
    <div className={`rounded-2xl border p-4 ${TONE[r.level]}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold"><Icon size={16} />{title}</div>
        <span className="rounded-full bg-white/70 px-2.5 py-0.5 text-xs font-bold">{r.label}</span>
      </div>
      {r.message && <p className="mt-2 text-xs leading-relaxed">{r.message}</p>}
      {r.parameters.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs">
          {r.parameters.map((p) => (
            <li key={p.key} className="flex justify-between gap-2 rounded-lg bg-white/60 px-2 py-1">
              <span className="text-slate-600">{p.label}</span>
              <span className={PARAM[p.status]}>{p.value} {p.unit}{p.reference ? <span className="ml-1 font-normal text-slate-400">({p.reference})</span> : null}</span>
            </li>
          ))}
        </ul>
      )}
      {r.source_date && <p className="mt-2 text-[11px] opacity-80">Source report: {fmtDate(r.source_date)}</p>}
    </div>
  )
}

export default function RiskCards({ risk }) {
  return (
    <div>
      <div className="grid gap-3 md:grid-cols-3">
        <Card title="Kidney risk" icon={Droplets} r={risk.kidney} />
        <Card title="Heart risk" icon={HeartPulse} r={risk.heart} />
        <Card title="Liver risk" icon={Activity} r={risk.liver} />
      </div>
      <p className="mt-3 text-xs text-slate-500">{risk.method} · Calculated {fmtDate(risk.prediction_date)} · {risk.disclaimer}</p>
    </div>
  )
}
