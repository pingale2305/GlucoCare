import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Spinner } from './ui'

const pad = (n) => String(n).padStart(2, '0')
export const dayISO = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const HORIZON = 60
const WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const timeLabel = (iso) => new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })

/** Month calendar + free 40-minute slots. fetchSlots(dayISO) -> [{start, available}]. onChange(startISO | null). */
export default function SlotPicker({ fetchSlots, value, onChange, refreshKey = 0 }) {
  const today = useMemo(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d }, [])
  const last = useMemo(() => { const d = new Date(today); d.setDate(d.getDate() + HORIZON); return d }, [today])
  const [month, setMonth] = useState(new Date(today.getFullYear(), today.getMonth(), 1))
  const [day, setDay] = useState(null)
  const [slots, setSlots] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!day) return undefined
    let live = true
    setSlots(null); setError('')
    fetchSlots(day).then((s) => { if (live) setSlots(s) }).catch((e) => { if (live) { setSlots([]); setError(e?.response?.data?.detail || 'Could not load time slots') } })
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [day, refreshKey])

  const first = new Date(month.getFullYear(), month.getMonth(), 1)
  const offset = (first.getDay() + 6) % 7 // Monday first
  const count = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
  const cells = [...Array(offset).fill(null), ...Array.from({ length: count }, (_, i) => new Date(month.getFullYear(), month.getMonth(), i + 1))]
  const canPrev = month > new Date(today.getFullYear(), today.getMonth(), 1)
  const canNext = new Date(month.getFullYear(), month.getMonth() + 1, 1) <= last

  return (
    <div className="grid gap-5 md:grid-cols-[300px_1fr]">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <button type="button" className="rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-100 disabled:opacity-30" disabled={!canPrev} onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))} aria-label="Previous month"><ChevronLeft size={18} /></button>
          <div className="text-sm font-bold text-navy-900">{month.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}</div>
          <button type="button" className="rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-100 disabled:opacity-30" disabled={!canNext} onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))} aria-label="Next month"><ChevronRight size={18} /></button>
        </div>
        <div className="grid grid-cols-7 gap-1 text-center">
          {WEEK.map((w) => <div key={w} className="py-1 text-[11px] font-semibold text-slate-400">{w}</div>)}
          {cells.map((d, i) => {
            if (!d) return <div key={`e${i}`} />
            const off = d < today || d > last || d.getDay() === 0
            const sel = day === dayISO(d)
            const isToday = dayISO(d) === dayISO(today)
            return (
              <button key={dayISO(d)} type="button" disabled={off} onClick={() => { setDay(dayISO(d)); onChange(null) }}
                className={`aspect-square rounded-xl text-sm font-medium transition ${sel ? 'bg-navy-900 text-white shadow' : off ? 'cursor-not-allowed text-slate-300' : 'text-slate-700 hover:bg-brand-50 hover:text-brand-800'} ${isToday && !sel ? 'ring-1 ring-brand-400' : ''}`}>
                {d.getDate()}
              </button>
            )
          })}
        </div>
        <p className="mt-2 text-xs text-slate-400">Monday to Saturday · 40-minute Zoom calls</p>
      </div>
      <div>
        <div className="mb-2 text-sm font-semibold text-slate-700">{day ? new Date(`${day}T00:00`).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' }) : 'Select a date'}</div>
        {!day ? <div className="grid h-40 place-items-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400">Pick a day on the calendar to see free times</div>
          : slots === null ? <div className="grid h-40 place-items-center"><Spinner /></div>
            : error ? <div className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
              : slots.length === 0 ? <div className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No slots on this day.</div>
                : (
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {slots.map((s) => (
                      <button key={s.start} type="button" disabled={!s.available} onClick={() => onChange(s.start)}
                        className={`rounded-xl border px-3 py-2.5 text-sm font-semibold transition ${value === s.start ? 'border-brand-600 bg-brand-600 text-white shadow' : s.available ? 'border-slate-200 bg-white text-slate-700 hover:border-brand-400 hover:bg-brand-50' : 'cursor-not-allowed border-slate-100 bg-slate-50 text-slate-300 line-through'}`}>
                        {timeLabel(s.start)}
                      </button>
                    ))}
                  </div>
                )}
      </div>
    </div>
  )
}
