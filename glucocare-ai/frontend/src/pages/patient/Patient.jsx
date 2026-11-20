import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Activity, CheckCircle2, Droplet, Footprints, UserRound, Pencil, Ruler, Scale, UploadCloud, Utensils } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import api, { errMsg } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { Async, Badge, Card, CardHeader, Empty, Field, Modal, PageHeader, Spinner, Stat, Table } from '../../components/ui'
import { GlucoseChart } from '../../components/charts'
import ReportTable from '../../components/ReportTable'
import { GROUPS, LabFields } from '../../components/LabEntryForm'
import { CONTEXT, NA, bmiBand, bmiOf, fmtDate, fmtDateTime, fmtNum, glucoseTone, greeting, nowLocalInput, todayISO } from '../../utils/format'

const usePid = () => useAuth().user.patient_id
const Alert = ({ msg, ok }) => msg ? <div role="alert" className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm ${ok ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{ok && <CheckCircle2 size={15} />}{msg}</div> : null

function BodyForm({ pid, body, onSaved }) {
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm({ defaultValues: { height_cm: body.height_cm ?? '', weight_kg: body.weight_kg ?? '' } })
  const [error, setError] = useState('')
  const bmi = bmiOf(+watch('height_cm'), +watch('weight_kg'))
  const submit = async (v) => {
    setError('')
    try { await api.put(`/api/patients/${pid}/body`, { height_cm: +v.height_cm, weight_kg: +v.weight_kg }); onSaved() } catch (e) { setError(errMsg(e)) }
  }
  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Height (cm)" error={errors.height_cm?.message}><input type="number" step="0.1" className="input" {...register('height_cm', { required: 'Required', min: { value: 50, message: '50–250' }, max: { value: 250, message: '50–250' } })} /></Field>
        <Field label="Weight (kg)" error={errors.weight_kg?.message}><input type="number" step="0.1" className="input" {...register('weight_kg', { required: 'Required', min: { value: 10, message: '10–400' }, max: { value: 400, message: '10–400' } })} /></Field>
      </div>
      <div className="flex items-center justify-between rounded-xl bg-brand-50 px-4 py-3 text-sm"><span className="text-slate-600">BMI (calculated)</span><span className="text-lg font-bold text-brand-800">{bmi ?? '—'}{bmi ? <span className="ml-2 text-xs font-medium text-slate-500">{bmiBand(bmi)}</span> : null}</span></div>
      <Alert msg={error} />
      <button className="btn-primary w-full" disabled={isSubmitting}>{isSubmitting && <Spinner size={16} />}Save</button>
    </form>
  )
}

export function PatientDashboard() {
  const pid = usePid()
  const { user } = useAuth()
  const st = useFetch(() => api.get(`/api/patients/${pid}`).then((r) => r.data), [pid])
  const [edit, setEdit] = useState(false)
  return (
    <>
      <PageHeader title={`${greeting()}, ${user.full_name.split(' ')[0]}`} />
      <Async state={st}>{(d) => {
        const g = d.latest_glucose, b = d.body
        return (
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Stat label="Patient" value={<span className="text-xl">{d.profile.display_name || user.full_name}</span>} hint={`${d.profile.sex === 'M' ? 'Male' : d.profile.sex === 'F' ? 'Female' : ''}${d.profile.sex && d.profile.age != null ? ', ' : ''}${d.profile.age != null ? d.profile.age + ' yrs' : ''}` || undefined} icon={UserRound} tone="slate" />
              <Stat label="Patient ID" value={<span className="text-2xl">{d.profile.patient_code}</span>} icon={UserRound} tone="blue" />
              <Stat label="Latest glucose" value={g ? g.value : '—'} unit={g ? 'mg/dL' : undefined} hint={g ? `${CONTEXT[g.context]} · ${fmtDateTime(g.at)}` : NA} icon={Droplet} tone="teal" />
              <Stat label="Latest HbA1c" value={d.latest_hba1c.value != null ? d.latest_hba1c.value : '—'} unit={d.latest_hba1c.value != null ? '%' : undefined} hint={d.latest_hba1c.value != null ? fmtDate(d.latest_hba1c.date) : NA} icon={Activity} tone="violet" />
            </div>
            <Card>
              <CardHeader title="Height, weight and BMI" icon={Scale} subtitle={b.measured_on ? `Last updated ${fmtDate(b.measured_on)}${b.source === 'inbody_import' ? ' · InBody record' : ''}` : undefined}
                action={<button className="btn-ghost" onClick={() => setEdit(true)}><Pencil size={14} />{b.weight_kg ? 'Update' : 'Add'}</button>} />
              <div className="grid divide-y divide-slate-100 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
                {[['Height', b.height_cm, 'cm', Ruler], ['Weight', b.weight_kg, 'kg', Scale], ['BMI', b.bmi, bmiBand(b.bmi), Activity]].map(([l, v, u, I]) => (
                  <div key={l} className="flex items-center gap-4 p-5"><span className="grid h-11 w-11 place-items-center rounded-xl bg-slate-100 text-slate-500"><I size={19} /></span>
                    <div><div className="text-xs font-semibold text-slate-500">{l}</div>
                      <div className="text-2xl font-bold text-navy-900">{v != null ? fmtNum(v) : <span className="text-base font-medium text-slate-400">{NA}</span>}{v != null && u ? <span className="ml-1.5 text-sm font-medium text-slate-500">{u}</span> : null}</div></div></div>
                ))}
              </div>
            </Card>
            <Modal open={edit} onClose={() => setEdit(false)} title="Height and weight">
              <BodyForm pid={pid} body={b} onSaved={() => { setEdit(false); st.reload() }} />
            </Modal>
          </div>
        )
      }}</Async>
    </>
  )
}

export function PatientGlucose() {
  const pid = usePid()
  const st = useFetch(() => api.get(`/api/patients/${pid}/glucose`).then((r) => r.data.items), [pid])
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm({ defaultValues: { measured_at: nowLocalInput(), context: 'fasting' } })
  const [msg, setMsg] = useState({ text: '', ok: false })
  const submit = async (v) => {
    setMsg({ text: '' })
    try {
      await api.post(`/api/patients/${pid}/glucose`, { measured_at: v.measured_at, value_mg_dl: +v.value_mg_dl, context: v.context })
      setMsg({ text: 'Reading saved.', ok: true }); reset({ measured_at: nowLocalInput(), context: v.context, value_mg_dl: '' }); st.reload()
    } catch (e) { setMsg({ text: errMsg(e) }) }
  }
  return (
    <>
      <PageHeader title="My Glucose Readings" />
      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <Card className="self-start">
          <CardHeader title="Add a reading" icon={Droplet} />
          <form onSubmit={handleSubmit(submit)} className="space-y-4 p-5" noValidate>
            <Field label="Glucose (mg/dL)" error={errors.value_mg_dl?.message}><input type="number" step="1" inputMode="numeric" className="input !text-lg !font-semibold" {...register('value_mg_dl', { required: 'Enter the reading', min: { value: 20, message: '20–600' }, max: { value: 600, message: '20–600' } })} /></Field>
            <Field label="When was it taken?"><select className="input" {...register('context')}>{Object.entries(CONTEXT).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
            <Field label="Date and time" error={errors.measured_at?.message}><input type="datetime-local" className="input" max={nowLocalInput()} {...register('measured_at', { required: 'Select date and time' })} /></Field>
            <Alert msg={msg.text} ok={msg.ok} />
            <button className="btn-primary w-full" disabled={isSubmitting}>{isSubmitting && <Spinner size={16} />}Save reading</button>
          </form>
        </Card>
        <div className="space-y-6">
          <Card><CardHeader title="Glucose history" subtitle="Shaded band: 70–180 mg/dL" /><div className="p-4"><Async state={st}>{(items) => <GlucoseChart readings={items} />}</Async></div></Card>
          <Card><CardHeader title="Previous readings" />
            <Async state={st}>{(items) => items.length === 0 ? <Empty title="No readings yet" hint="Your saved readings will appear here." /> : (
              <div className="max-h-[420px] overflow-auto"><Table head={['Date and time', 'Reading', 'Type']}>
                {items.map((r) => (
                  <tr key={r.id} className="transition hover:bg-slate-50"><td className="td text-slate-600">{fmtDateTime(r.measured_at)}</td>
                    <td className={`td text-base font-bold ${glucoseTone(r.value_mg_dl)}`}>{r.value_mg_dl} <span className="text-xs font-medium text-slate-400">mg/dL</span></td>
                    <td className="td"><Badge tone="teal">{CONTEXT[r.context]}</Badge></td></tr>
                ))}</Table></div>
            )}</Async>
          </Card>
        </div>
      </div>
    </>
  )
}

export function PatientReports() {
  const pid = usePid()
  const st = useFetch(() => api.get(`/api/patients/${pid}/reports`).then((r) => r.data.items), [pid])
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm({ defaultValues: { report_type: 'lab_report' } })
  const [msg, setMsg] = useState({ text: '', ok: false })
  const submit = async (v) => {
    setMsg({ text: '' })
    const fd = new FormData()
    fd.append('title', v.title.trim()); fd.append('report_type', v.report_type)
    if (v.report_date) fd.append('report_date', v.report_date)
    fd.append('file', v.file[0])
    const lab = {}
    GROUPS.forEach(([, fields]) => fields.forEach(([k]) => { if (v[k] !== '' && v[k] != null) lab[k] = Number(v[k]) }))
    if (Object.keys(lab).length) fd.append('lab_values', JSON.stringify(lab))
    try { await api.post(`/api/patients/${pid}/reports`, fd); setMsg({ text: 'Report uploaded.', ok: true }); reset({ report_type: v.report_type, title: '', report_date: '', ...Object.fromEntries(GROUPS.flatMap(([, f]) => f.map(([k]) => [k, '']))) }); st.reload() }
    catch (e) { setMsg({ text: errMsg(e) }) }
  }
  return (
    <>
      <PageHeader title="My Reports" />
      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <Card className="self-start">
          <CardHeader title="Upload a report" icon={UploadCloud} />
          <form onSubmit={handleSubmit(submit)} className="space-y-4 p-5" noValidate>
            <Field label="Report name" error={errors.title?.message}><input className="input" placeholder="e.g. HbA1c – March" {...register('title', { required: 'Enter a name', minLength: { value: 2, message: 'Too short' } })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Type"><select className="input" {...register('report_type')}><option value="lab_report">Lab report</option><option value="prescription">Prescription</option><option value="scan">Scan</option><option value="other">Other</option></select></Field>
              <Field label="Report date"><input type="date" className="input" max={todayISO()} {...register('report_date')} /></Field>
            </div>
            <Field label="File" error={errors.file?.message} hint="PDF, PNG, JPG, XLSX or CSV · up to 10 MB">
              <input type="file" accept=".pdf,.png,.jpg,.jpeg,.xlsx,.csv" className="input !p-1.5 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-brand-800"
                {...register('file', { validate: (f) => (f && f.length ? (f[0].size <= 10 * 1048576 || 'File is larger than 10 MB') : 'Choose a file') })} />
            </Field>
            <details className="rounded-xl border border-slate-200 open:bg-slate-50/60">
              <summary className="cursor-pointer select-none px-3.5 py-2.5 text-sm font-semibold text-brand-800">Values from this report (optional)</summary>
              <div className="space-y-4 px-3.5 pb-4 pt-1"><LabFields register={register} cols="grid-cols-2" /></div>
            </details>
            <Alert msg={msg.text} ok={msg.ok} />
            <button className="btn-primary w-full" disabled={isSubmitting}>{isSubmitting && <Spinner size={16} />}Upload</button>
          </form>
        </Card>
        <Card><CardHeader title="Uploaded reports" /><Async state={st}>{(items) => <ReportTable items={items} />}</Async></Card>
      </div>
    </>
  )
}

function FoodTab({ pid }) {
  const st = useFetch(() => api.get(`/api/patients/${pid}/food`).then((r) => r.data.items), [pid])
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm({ defaultValues: { entry_date: todayISO(), meal_type: 'Breakfast' } })
  const [msg, setMsg] = useState({ text: '', ok: false })
  const submit = async (v) => {
    setMsg({ text: '' })
    try { await api.post(`/api/patients/${pid}/food`, { entry_date: v.entry_date, meal_type: v.meal_type, items: v.items }); setMsg({ text: 'Food entry saved.', ok: true }); reset({ entry_date: v.entry_date, meal_type: v.meal_type, items: '' }); st.reload() }
    catch (e) { setMsg({ text: errMsg(e) }) }
  }
  return (
    <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
      <Card className="self-start"><CardHeader title="Add food intake" icon={Utensils} />
        <form onSubmit={handleSubmit(submit)} className="space-y-4 p-5" noValidate>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Date" error={errors.entry_date?.message}><input type="date" className="input" max={todayISO()} {...register('entry_date', { required: 'Select a date' })} /></Field>
            <Field label="Meal"><select className="input" {...register('meal_type')}>{['Breakfast', 'Lunch', 'Snacks', 'Dinner'].map((m) => <option key={m}>{m}</option>)}</select></Field>
          </div>
          <Field label="Food items" error={errors.items?.message}><textarea rows={3} className="input" placeholder="e.g. 2 rotis, dal, salad" {...register('items', { required: 'Enter what you ate', minLength: { value: 2, message: 'Too short' }, maxLength: { value: 500, message: 'Max 500 characters' } })} /></Field>
          <Alert msg={msg.text} ok={msg.ok} />
          <button className="btn-primary w-full" disabled={isSubmitting}>{isSubmitting && <Spinner size={16} />}Save entry</button>
        </form></Card>
      <Card><CardHeader title="Previous food entries" />
        <Async state={st}>{(items) => items.length === 0 ? <Empty title="No food entries yet" /> : (
          <div className="max-h-[480px] overflow-auto"><Table head={['Date', 'Meal', 'Food items']}>
            {items.map((f) => <tr key={f.id} className="hover:bg-slate-50"><td className="td whitespace-nowrap text-slate-600">{fmtDate(f.entry_date)}</td><td className="td"><Badge tone="teal">{f.meal_type}</Badge></td><td className="td">{f.items}</td></tr>)}
          </Table></div>)}</Async></Card>
    </div>
  )
}

function StepsTab({ pid }) {
  const st = useFetch(() => api.get(`/api/patients/${pid}/steps`).then((r) => r.data.items), [pid])
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm({ defaultValues: { entry_date: todayISO() } })
  const [msg, setMsg] = useState({ text: '', ok: false })
  const submit = async (v) => {
    setMsg({ text: '' })
    try { await api.post(`/api/patients/${pid}/steps`, { entry_date: v.entry_date, steps: parseInt(v.steps, 10) }); setMsg({ text: 'Steps saved.', ok: true }); reset({ entry_date: v.entry_date, steps: '' }); st.reload() }
    catch (e) { setMsg({ text: errMsg(e) }) }
  }
  return (
    <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
      <Card className="self-start"><CardHeader title="Add walking steps" icon={Footprints} subtitle="Saving the same date again updates it" />
        <form onSubmit={handleSubmit(submit)} className="space-y-4 p-5" noValidate>
          <Field label="Date" error={errors.entry_date?.message}><input type="date" className="input" max={todayISO()} {...register('entry_date', { required: 'Select a date' })} /></Field>
          <Field label="Steps walked" error={errors.steps?.message}><input type="number" inputMode="numeric" className="input !text-lg !font-semibold" {...register('steps', { required: 'Enter the steps', min: { value: 0, message: 'Cannot be negative' }, max: { value: 100000, message: 'Too high' } })} /></Field>
          <Alert msg={msg.text} ok={msg.ok} />
          <button className="btn-primary w-full" disabled={isSubmitting}>{isSubmitting && <Spinner size={16} />}Save steps</button>
        </form></Card>
      <Card><CardHeader title="Previous walking records" />
        <Async state={st}>{(items) => items.length === 0 ? <Empty title="No walking records yet" /> : (
          <div className="max-h-[480px] overflow-auto"><Table head={['Date', 'Steps']}>
            {items.map((s) => <tr key={s.id} className="hover:bg-slate-50"><td className="td text-slate-600">{fmtDate(s.entry_date)}</td><td className="td font-semibold">{s.steps.toLocaleString()}</td></tr>)}
          </Table></div>)}</Async></Card>
    </div>
  )
}

export function PatientFollowUps() {
  const pid = usePid()
  const [tab, setTab] = useState('food')
  const sg = useFetch(() => api.get(`/api/patients/${pid}/suggestions`).then((r) => r.data.items), [pid])
  return (
    <>
      <PageHeader title="Follow-ups" />
      <Card className="mb-6 border-l-4 !border-l-brand-500">
        <CardHeader title="Doctor’s suggestions" />
        <Async state={sg}>{(items) => items.length === 0 ? <Empty title="No suggestions yet" hint="Suggestions from your doctor will appear here." /> : (
          <div className="p-5">
            <div className="whitespace-pre-wrap text-[15px] leading-relaxed text-slate-800">{items[0].content}</div>
            <div className="mt-3 text-xs text-slate-500">{items[0].doctor_name} · {fmtDate(items[0].suggestion_date)}</div>
            {items.length > 1 && (
              <details className="mt-4 border-t border-slate-100 pt-3"><summary className="cursor-pointer text-sm font-semibold text-brand-700">Earlier suggestions ({items.length - 1})</summary>
                <ul className="mt-3 space-y-3">{items.slice(1).map((s) => <li key={s.id} className="rounded-xl bg-slate-50 p-3 text-sm"><div className="whitespace-pre-wrap text-slate-700">{s.content}</div><div className="mt-1.5 text-xs text-slate-400">{fmtDate(s.suggestion_date)}</div></li>)}</ul></details>
            )}
          </div>)}</Async>
      </Card>
      <div className="mb-5 inline-flex gap-1 rounded-xl bg-slate-100 p-1">
        {[['food', 'Food intake', Utensils], ['steps', 'Walking steps', Footprints]].map(([k, l, I]) => (
          <button key={k} onClick={() => setTab(k)} className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition ${tab === k ? 'bg-white text-navy-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}><I size={15} />{l}</button>
        ))}
      </div>
      {tab === 'food' ? <FoodTab pid={pid} /> : <StepsTab pid={pid} />}
    </>
  )
}
