import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { CheckCircle2, Search, X } from 'lucide-react'
import api, { errMsg } from '../services/api'
import { nameOrId, todayISO } from '../utils/format'
import { Field, Spinner } from './ui'

/** Type-ahead picker over the doctor's assigned patients. */
export function PatientPicker({ value, onChange }) {
  const [q, setQ] = useState('')
  const [items, setItems] = useState([])
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (!open) return undefined
    const t = setTimeout(() => api.get('/api/doctor/patients', { params: { search: q, page_size: 8 } }).then((r) => setItems(r.data.items)).catch(() => setItems([])), 200)
    return () => clearTimeout(t)
  }, [q, open])
  if (value) return (
    <div className="input flex items-center justify-between !py-2"><span className="font-medium">{nameOrId(value)} <span className="text-xs text-slate-400">{value.patient_code}</span></span>
      <button type="button" aria-label="Clear patient" onClick={() => onChange(null)} className="rounded p-1 text-slate-400 hover:bg-slate-100"><X size={15} /></button></div>
  )
  return (
    <div className="relative">
      <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
      <input className="input !pl-9" placeholder="Search by patient ID or name" value={q} onFocus={() => setOpen(true)} onChange={(e) => { setQ(e.target.value); setOpen(true) }} />
      {open && (
        <ul className="card absolute z-20 mt-1 max-h-64 w-full overflow-auto py-1">
          {items.length === 0 && <li className="px-3 py-2 text-sm text-slate-400">No matching patients</li>}
          {items.map((p) => (
            <li key={p.id}><button type="button" className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50" onClick={() => { onChange(p); setOpen(false); setQ('') }}>
              <span className="font-medium">{nameOrId(p)}</span><span className="text-xs text-slate-400">{p.patient_code}</span></button></li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** One simple suggestion form: patient, suggestion text, date. Edits when `editing` is given. */
export default function SuggestionForm({ fixedPatient, editing, onSaved, onCancel }) {
  const [patient, setPatient] = useState(fixedPatient || null)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm({
    defaultValues: { content: editing?.content || '', suggestion_date: editing?.suggestion_date || todayISO() },
  })
  useEffect(() => { reset({ content: editing?.content || '', suggestion_date: editing?.suggestion_date || todayISO() }) }, [editing, reset])
  const submit = async (v) => {
    setError(''); setOk('')
    const pid = editing ? editing.patient_id : patient?.id
    if (!pid) { setError('Select a patient'); return }
    try {
      if (editing) await api.put(`/api/doctor/suggestions/${editing.id}`, { content: v.content, suggestion_date: v.suggestion_date })
      else await api.post(`/api/doctor/patients/${pid}/suggestions`, { content: v.content, suggestion_date: v.suggestion_date })
      setOk(editing ? 'Suggestion updated.' : 'Suggestion saved.')
      if (!editing) reset({ content: '', suggestion_date: todayISO() })
      onSaved?.()
    } catch (e) { setError(errMsg(e)) }
  }
  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
      {!fixedPatient && !editing && <Field label="Select patient"><PatientPicker value={patient} onChange={setPatient} /></Field>}
      <Field label="Doctor suggestion" error={errors.content?.message}>
        <textarea rows={7} className="input !text-[15px] !leading-relaxed" placeholder="Diet, activity, medication instructions and follow-up tests — all in one note."
          {...register('content', { required: 'Write the suggestion', minLength: { value: 3, message: 'Too short' }, maxLength: { value: 4000, message: 'Max 4000 characters' } })} />
      </Field>
      <Field label="Date" error={errors.suggestion_date?.message}><input type="date" className="input sm:max-w-[200px]" {...register('suggestion_date', { required: 'Select a date' })} /></Field>
      {error && <div role="alert" className="rounded-xl bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</div>}
      {ok && <div className="flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2.5 text-sm text-emerald-700"><CheckCircle2 size={15} />{ok}</div>}
      <div className="flex gap-2">
        <button className="btn-primary" disabled={isSubmitting}>{isSubmitting && <Spinner size={16} />}{editing ? 'Update suggestion' : 'Save suggestion'}</button>
        {editing && <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  )
}
