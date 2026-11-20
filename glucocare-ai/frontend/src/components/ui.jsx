import { AlertTriangle, ChevronLeft, ChevronRight, Inbox, Loader2, X } from 'lucide-react'
import { SEV } from '../utils/format'

export const Card = ({ className = '', children }) => <div className={`card ${className}`}>{children}</div>

export const CardHeader = ({ title, subtitle, action, icon: Icon }) => (
  <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
    <div className="flex items-center gap-2.5">
      {Icon && <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-50 text-brand-700"><Icon size={16} /></span>}
      <div>
        <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>
    </div>
    {action}
  </div>
)

export const PageHeader = ({ title, subtitle, actions }) => (
  <div className="mb-6 flex flex-wrap items-end justify-between gap-3 animate-fadeUp">
    <div>
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
    </div>
    <div className="flex flex-wrap items-center gap-2">{actions}</div>
  </div>
)

const TONES = {
  teal: 'bg-brand-50 text-brand-800', pink: 'bg-rose-50 text-rose-700', green: 'bg-emerald-50 text-emerald-700',
  blue: 'bg-sky-50 text-sky-700', amber: 'bg-amber-50 text-amber-700', slate: 'bg-slate-100 text-slate-700', violet: 'bg-violet-50 text-violet-700',
}
export const Stat = ({ label, value, hint, icon: Icon, tone = 'teal', unit, onClick }) => (
  <div onClick={onClick} className={`rounded-2xl p-4 ${TONES[tone]} ${onClick ? 'cursor-pointer transition hover:shadow-md' : ''} animate-fadeUp`}>
    <div className="flex items-center gap-2 text-xs font-semibold opacity-80">{Icon && <Icon size={14} />}{label}</div>
    <div className="mt-2 flex items-baseline gap-1.5"><span className="text-3xl font-bold">{value}</span>{unit && <span className="text-sm opacity-70">{unit}</span>}</div>
    {hint && <div className="mt-1 text-xs opacity-75">{hint}</div>}
  </div>
)

export const Badge = ({ children, tone = 'slate', className = '' }) => {
  const t = { slate: 'bg-slate-100 text-slate-700', green: 'bg-emerald-100 text-emerald-700', teal: 'bg-brand-100 text-brand-800', amber: 'bg-amber-100 text-amber-700', rose: 'bg-rose-100 text-rose-700', blue: 'bg-sky-100 text-sky-700', violet: 'bg-violet-100 text-violet-700' }[tone]
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${t} ${className}`}>{children}</span>
}

export const SeverityBadge = ({ severity }) => {
  const s = SEV[severity] || SEV.info
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${s.cls}`}><span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />{s.label}</span>
}

export const Spinner = ({ size = 18 }) => <Loader2 size={size} className="animate-spin text-brand-600" />
export const Loading = ({ label = 'Loading…' }) => <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500"><Spinner />{label}</div>
export const ErrorBox = ({ message, onRetry }) => (
  <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
    <AlertTriangle size={18} className="mt-0.5 shrink-0" />
    <div className="flex-1">{message}</div>
    {onRetry && <button onClick={onRetry} className="font-medium underline">Retry</button>}
  </div>
)
export const Empty = ({ title = 'Nothing here yet', hint, action }) => (
  <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
    <span className="grid h-11 w-11 place-items-center rounded-full bg-slate-100 text-slate-400"><Inbox size={20} /></span>
    <div className="text-sm font-medium text-slate-700">{title}</div>
    {hint && <div className="max-w-sm text-xs text-slate-500">{hint}</div>}
    {action}
  </div>
)
export const Async = ({ state, children }) => (state.loading && !state.data ? <Loading /> : state.error ? <ErrorBox message={state.error} onRetry={state.reload} /> : children(state.data))

export const Field = ({ label, error, hint, children }) => (
  <label className="block">
    <span className="mb-1 block text-xs font-semibold text-slate-600">{label}</span>
    {children}
    {hint && !error && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
    {error && <span className="mt-1 block text-xs text-rose-600">{error}</span>}
  </label>
)

export const Modal = ({ open, onClose, title, children, wide }) => {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4" onClick={onClose}>
      <div className={`card max-h-[90vh] w-full overflow-auto ${wide ? 'max-w-2xl' : 'max-w-md'} animate-fadeUp`} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h3 className="font-semibold">{title}</h3>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100"><X size={18} /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export const Tabs = ({ tabs, value, onChange }) => (
  <div className="flex gap-1 overflow-x-auto border-b border-slate-200">
    {tabs.map((t) => (
      <button key={t.id} onClick={() => onChange(t.id)}
        className={`flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3.5 py-2.5 text-sm font-medium transition ${value === t.id ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>
        {t.icon && <t.icon size={15} />}{t.label}{t.badge ? <span className="ml-1 rounded-full bg-rose-100 px-1.5 text-[10px] font-bold text-rose-700">{t.badge}</span> : null}
      </button>
    ))}
  </div>
)

export const Pagination = ({ page, pageSize, total, onPage }) => {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-xs text-slate-500">
      <span>{total === 0 ? 'No results' : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total.toLocaleString()}`}</span>
      <div className="flex items-center gap-1">
        <button className="btn-ghost !px-2 !py-1" disabled={page <= 1} onClick={() => onPage(page - 1)}><ChevronLeft size={14} /></button>
        <span className="px-2">Page {page} / {pages}</span>
        <button className="btn-ghost !px-2 !py-1" disabled={page >= pages} onClick={() => onPage(page + 1)}><ChevronRight size={14} /></button>
      </div>
    </div>
  )
}

export const Disclaimer = ({ children }) => (
  <p className="rounded-xl bg-slate-100 px-3 py-2 text-xs leading-relaxed text-slate-500">{children}</p>
)

export const Table = ({ head, children, empty }) => (
  <div className="overflow-x-auto">
    <table className="w-full min-w-[640px] text-left">
      <thead className="bg-slate-50"><tr>{head.map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
      <tbody className="divide-y divide-slate-100">{children}</tbody>
    </table>
    {empty}
  </div>
)
