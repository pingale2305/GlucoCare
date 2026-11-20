import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Check, FilePlus2 } from 'lucide-react'
import api, { errMsg } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { Async, Badge, Card, CardHeader, Empty, Modal, SeverityBadge, Tabs } from '../../components/ui'
import LabEntryForm from '../../components/LabEntryForm'
import { GlucoseChart, HbA1cChart, StepsChart } from '../../components/charts'
import ReportTable from '../../components/ReportTable'
import RiskCards from '../../components/RiskCards'
import SuggestionForm from '../../components/SuggestionForm'
import { CONTEXT, NA, SOURCE, fmtDate, fmtDateTime, fmtNum, glucoseTone, initials } from '../../utils/format'

const Metric = ({ label, value, unit, sub }) => (
  <div className="rounded-xl bg-slate-50 px-4 py-3">
    <div className="text-xs font-semibold text-slate-500">{label}</div>
    <div className="mt-0.5 text-xl font-bold text-navy-900">{value ?? <span className="text-sm font-medium text-slate-400">{NA}</span>}{value != null && unit ? <span className="ml-1 text-xs font-medium text-slate-500">{unit}</span> : null}</div>
    {sub && <div className="text-[11px] text-slate-400">{sub}</div>}
  </div>
)

function LabTable({ labs, onAdd }) {
  const items = labs.items.slice(0, 6) // newest first
  const rows = useMemo(() => labs.parameters.filter((p) => items.some((r) => r.values[p.key] != null)), [labs, items])
  const hba1c = useMemo(() => [...labs.items].reverse().filter((r) => r.values.hba1c != null).map((r) => ({ date: r.collected_on, value: r.values.hba1c })), [labs])
  let group = null
  const add = <button className="btn-ghost !py-1.5" onClick={onAdd}><FilePlus2 size={14} />Enter values from a report</button>
  if (!labs.items.length) return <Empty title="No laboratory values" hint="Values appear here when the patient adds them while uploading a report. You can also type them in." action={add} />
  return (
    <div className="space-y-5">
      <div className="flex justify-end px-5 pt-4">{add}</div>
      <div className="px-5"><div className="mb-1 text-sm font-semibold text-slate-700">HbA1c trend</div><HbA1cChart series={hba1c} height={220} /></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-left">
        <thead className="bg-slate-50"><tr><th className="th">Parameter</th><th className="th">Reference</th>{items.map((r) => <th key={r.collected_on + r.source} className="th text-right">{fmtDate(r.collected_on)}{r.source === 'doctor_entered' && <div className="text-[10px] font-medium text-emerald-600">Doctor-entered</div>}{r.source === 'patient_entered' && <div className="text-[10px] font-medium text-sky-600">Patient-entered</div>}</th>)}</tr></thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((p) => {
            const head = p.group !== group ? (group = p.group, <tr key={`g-${p.group}`} className="bg-slate-50/70"><td colSpan={items.length + 2} className="px-4 py-1.5 text-xs font-bold text-brand-800">{p.group}</td></tr>) : null
            return [head, (
              <tr key={p.key}><td className="td font-medium">{p.label}{p.unit && <span className="ml-1 text-xs text-slate-400">{p.unit}</span>}</td><td className="td text-xs text-slate-500">{p.reference || '—'}</td>
                {items.map((r) => { const v = r.values[p.key], f = r.flags[p.key]; return (
                  <td key={r.collected_on + r.source} className={`td text-right tabular-nums ${f ? 'font-bold' : ''} ${f === 'H' ? 'text-rose-600' : f === 'L' ? 'text-sky-600' : ''}`}>{v != null ? fmtNum(v, 2) : <span className="text-slate-300">—</span>}{f && <sup className="ml-0.5 text-[10px]">{f}</sup>}</td>) })}
              </tr>)]
          })}
        </tbody></table></div>
      <p className="px-5 pb-4 text-xs text-slate-400">Imported EHC records and report values entered by the patient or doctor. H = above range, L = below range.</p>
    </div>
  )
}

const Plain = ({ head, children }) => <div className="max-h-[420px] overflow-auto"><table className="w-full min-w-[520px] text-left"><thead className="sticky top-0 bg-slate-50"><tr>{head.map((h) => <th key={h} className="th">{h}</th>)}</tr></thead><tbody className="divide-y divide-slate-100">{children}</tbody></table></div>

function InBody({ items }) {
  if (!items.length) return <Empty title="No InBody records" />
  return (
    <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left">
      <thead className="bg-slate-50"><tr>{['Date', 'Height (cm)', 'Weight (kg)', 'BMI', 'Body fat %', 'Skeletal muscle (kg)', 'Visceral fat', 'BMR', 'Source'].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
      <tbody className="divide-y divide-slate-100">{items.map((s) => (
        <tr key={s.test_datetime}><td className="td whitespace-nowrap">{fmtDateTime(s.test_datetime)}</td>
          {['height_cm', 'weight_kg', 'bmi', 'body_fat_percent', 'skeletal_muscle_mass', 'visceral_fat_level', 'bmr'].map((k) => <td key={k} className="td tabular-nums">{s[k] != null ? fmtNum(s[k]) : <span className="text-slate-300">—</span>}</td>)}
          <td className="td"><Badge tone={s.source === 'inbody_import' ? 'blue' : 'green'}>{s.source === 'inbody_import' ? 'Imported' : 'Patient-entered'}</Badge></td></tr>
      ))}</tbody></table></div>
  )
}

function Activity({ food, steps }) {
  return (
    <div className="grid gap-px bg-slate-100 xl:grid-cols-2">
      <div className="bg-white"><div className="px-5 py-3 text-sm font-semibold text-slate-700">Food intake</div>
        {food.length === 0 ? <Empty title="No food entries" /> : <Plain head={['Date', 'Meal', 'Items']}>{food.map((f) => <tr key={f.id}><td className="td whitespace-nowrap text-slate-600">{fmtDate(f.entry_date)}</td><td className="td"><Badge tone="teal">{f.meal_type}</Badge></td><td className="td">{f.items}</td></tr>)}</Plain>}</div>
      <div className="bg-white"><div className="px-5 py-3 text-sm font-semibold text-slate-700">Walking steps</div>
        <div className="px-3"><StepsChart steps={steps} height={180} /></div>
        {steps.length > 0 && <Plain head={['Date', 'Steps']}>{steps.map((s) => <tr key={s.id}><td className="td text-slate-600">{fmtDate(s.entry_date)}</td><td className="td font-semibold">{s.steps.toLocaleString()}</td></tr>)}</Plain>}</div>
    </div>
  )
}

export default function PatientReview() {
  const { id } = useParams()
  const st = useFetch(() => api.get(`/api/doctor/patients/${id}/review`).then((r) => r.data), [id])
  const [tab, setTab] = useState('labs')
  const [editing, setEditing] = useState(null)
  const [labForm, setLabForm] = useState(false)
  const [err, setErr] = useState('')
  const markReviewed = async (aid) => { try { setErr(''); await api.post(`/api/doctor/alerts/${aid}/review`, {}); st.reload() } catch (e) { setErr(errMsg(e)) } }
  return (
    <>
      <Link to="/doctor/patients" className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 transition hover:text-brand-700"><ArrowLeft size={15} />Patient Review & Alerts</Link>
      <Async state={st}>{(d) => {
        const p = d.profile, g = d.latest_glucose
        return (
          <div className="space-y-6">
            <Card className="p-5">
              <div className="flex flex-wrap items-center gap-4">
                <div className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-navy-900 text-lg font-bold text-brand-300">{initials(p.display_name || p.patient_code)}</div>
                <div className="min-w-0 flex-1">
                  <h1 className="truncate text-2xl font-extrabold text-navy-900">{p.display_name || <span className="text-slate-400">Name {NA}</span>}</h1>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500">
                    <span className="font-semibold text-slate-700">{p.patient_code}</span>{p.external_id && <span>{p.external_id}</span>}
                    <span>{p.age != null ? `${p.age} yrs` : `Age ${NA}`}</span><span>{p.sex === 'M' ? 'Male' : p.sex === 'F' ? 'Female' : `Gender ${NA}`}</span>
                    <Badge tone={p.source === 'self_registered' ? 'green' : 'blue'}>{SOURCE[p.source] || p.source}</Badge>
                  </div>
                </div>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
                <Metric label="Latest HbA1c" value={d.latest_hba1c.value != null ? fmtNum(d.latest_hba1c.value) : null} unit="%" sub={d.latest_hba1c.date ? fmtDate(d.latest_hba1c.date) : null} />
                <Metric label="Latest PPBS" value={d.latest_ppbs != null ? fmtNum(d.latest_ppbs, 0) : null} unit="mg/dL" />
                <Metric label="Latest glucose" value={g ? fmtNum(g.value, 0) : null} unit="mg/dL" sub={g ? `${g.source === 'lab' ? 'Lab fasting' : CONTEXT[g.context]} · ${fmtDate(g.at)}` : null} />
                <Metric label="Height" value={d.body.height_cm != null ? fmtNum(d.body.height_cm) : null} unit="cm" />
                <Metric label="Weight" value={d.body.weight_kg != null ? fmtNum(d.body.weight_kg) : null} unit="kg" />
                <Metric label="BMI" value={d.body.bmi != null ? fmtNum(d.body.bmi) : null} />
              </div>
            </Card>

            {d.alerts.length > 0 && (
              <Card><CardHeader title="Alerts" />
                {err && <div className="m-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
                <ul className="divide-y divide-slate-100">{d.alerts.map((a) => (
                  <li key={a.id} className="flex items-center gap-3 px-5 py-3"><SeverityBadge severity={a.severity} /><div className="flex-1 text-sm text-slate-700">{a.reason}<div className="text-xs text-slate-400">{a.reference_text}</div></div>
                    <button className="btn-ghost !px-2.5 !py-1.5 text-xs" onClick={() => markReviewed(a.id)}><Check size={13} />Reviewed</button></li>
                ))}</ul></Card>
            )}

            <Card><CardHeader title="Organ risk screening" /><div className="p-5"><RiskCards risk={d.risk} /></div></Card>

            <Card>
              <Tabs value={tab} onChange={setTab} tabs={[
                { id: 'labs', label: 'Lab reports' }, { id: 'inbody', label: 'InBody' }, { id: 'glucose', label: 'Glucose' },
                { id: 'activity', label: 'Food & steps' }, { id: 'reports', label: `Reports (${d.reports.length})` }, { id: 'suggestions', label: 'Suggestions' },
              ]} />
              {tab === 'labs' && <LabTable labs={d.labs} onAdd={() => setLabForm(true)} />}
              {tab === 'inbody' && <InBody items={d.inbody} />}
              {tab === 'glucose' && (d.readings.length === 0 ? <Empty title="No patient-entered readings" /> : (
                <div className="space-y-4 p-4"><GlucoseChart readings={d.readings} />
                  <Plain head={['Date and time', 'Reading', 'Type']}>{d.readings.map((r) => (
                    <tr key={r.id}><td className="td text-slate-600">{fmtDateTime(r.measured_at)}</td><td className={`td font-bold ${glucoseTone(r.value_mg_dl)}`}>{r.value_mg_dl} <span className="text-xs font-medium text-slate-400">mg/dL</span></td><td className="td"><Badge tone="teal">{CONTEXT[r.context]}</Badge></td></tr>))}</Plain></div>))}
              {tab === 'activity' && <Activity food={d.food} steps={d.steps} />}
              {tab === 'reports' && <ReportTable items={d.reports} />}
              {tab === 'suggestions' && (
                <div className="grid gap-px bg-slate-100 xl:grid-cols-[1fr_1fr]">
                  <div className="bg-white p-5"><div className="mb-3 text-sm font-semibold text-slate-700">{editing ? 'Edit suggestion' : 'New suggestion'}</div>
                    <SuggestionForm fixedPatient={{ id: p.id, display_name: p.display_name, patient_code: p.patient_code }} editing={editing} onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); st.reload() }} /></div>
                  <div className="bg-white"><div className="px-5 py-4 text-sm font-semibold text-slate-700">Previous suggestions</div>
                    {d.suggestions.length === 0 ? <Empty title="No suggestions yet" /> : (
                      <ul className="divide-y divide-slate-100">{d.suggestions.map((s) => (
                        <li key={s.id} className="px-5 py-4"><div className="flex items-center justify-between text-xs text-slate-400"><span>{fmtDate(s.suggestion_date)} · {s.doctor_name}</span>
                          <button className="font-semibold text-brand-700 hover:underline" onClick={() => setEditing(s)}>Edit</button></div>
                          <p className="mt-1.5 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{s.content}</p></li>))}</ul>)}</div>
                </div>
              )}
            </Card>
            <Modal open={labForm} onClose={() => setLabForm(false)} title="Enter values from a report" wide>
              <LabEntryForm patientId={p.id} onSaved={() => { setLabForm(false); st.reload() }} />
            </Modal>
          </div>
        )
      }}</Async>
    </>
  )
}
