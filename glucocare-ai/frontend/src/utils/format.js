export const NA = 'Not Available'
export const parseDate = (d) => {
  if (!d) return null
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(d))
  return m ? new Date(+m[1], +m[2] - 1, +m[3]) : new Date(d)
}
export const fmtDate = (d) => { const x = parseDate(d); return x && !isNaN(x) ? x.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—' }
export const fmtDateTime = (d) => { const x = d ? new Date(d) : null; return x && !isNaN(x) ? x.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—' }
export const fmtNum = (v, nd = 1) => (v === null || v === undefined || v === '' ? '—' : Number(v).toFixed(nd).replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1'))
export const greeting = () => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening' }
export const initials = (n = '') => n.split(' ').filter(Boolean).slice(0, 2).map((s) => s[0]).join('').toUpperCase() || 'U'
export const todayISO = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
export const nowLocalInput = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 16) }
export const bmiOf = (h, w) => (h > 0 && w > 0 ? Math.round((w / ((h / 100) ** 2)) * 10) / 10 : null)
export const bmiBand = (b) => (b == null ? '' : b < 18.5 ? 'Underweight' : b < 25 ? 'Normal' : b < 30 ? 'Overweight' : 'Obese')
export const nameOrId = (p) => p?.patient_name || p?.display_name || p?.external_id || p?.patient_code || '—'
export const CONTEXT = { fasting: 'Fasting', post_meal: 'Post-meal', random: 'Random', bedtime: 'Bedtime' }
export const SOURCE = { ehc_import: 'Imported (EHC)', inbody_import: 'Imported (InBody)', patient_entered: 'Patient-entered', self_registered: 'Self-registered', lab: 'Lab' }
export const SEV = {
  critical: { label: 'Critical', cls: 'bg-rose-100 text-rose-700 ring-rose-200', dot: 'bg-rose-500' },
  high: { label: 'High', cls: 'bg-orange-100 text-orange-700 ring-orange-200', dot: 'bg-orange-500' },
  moderate: { label: 'Moderate', cls: 'bg-amber-100 text-amber-700 ring-amber-200', dot: 'bg-amber-500' },
  info: { label: 'Info', cls: 'bg-sky-100 text-sky-700 ring-sky-200', dot: 'bg-sky-500' },
}
export const glucoseTone = (v) => (v == null ? 'text-slate-400' : v < 70 ? 'text-rose-600' : v > 180 ? 'text-amber-600' : 'text-emerald-600')
