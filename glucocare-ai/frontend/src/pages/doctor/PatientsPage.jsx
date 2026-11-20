import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AlertTriangle, Search, UserCheck } from 'lucide-react'
import api, { errMsg } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { Async, Card, Empty, Loading, PageHeader, Pagination, ErrorBox } from '../../components/ui'
import { fmtDate, fmtNum, glucoseTone } from '../../utils/format'

const Dash = () => <span className="text-slate-300">—</span>

export function PatientTable({ items }) {
  const navigate = useNavigate()
  if (!items.length) return <Empty title="No patients found" />
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] text-left">
        <thead className="bg-slate-50"><tr>
          {['Patient ID', 'Name', 'Age', 'Gender', 'HbA1c', 'PPBS', 'Glucose', 'Height', 'Weight', 'BMI'].map((h) => <th key={h} className="th">{h}</th>)}
        </tr></thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((p) => (
            <tr key={p.id} onClick={() => navigate(`/doctor/review/${p.id}`)} className="cursor-pointer transition hover:bg-brand-50/50">
              <td className="td"><div className="flex items-center gap-2 font-semibold text-navy-900">{p.patient_code}{p.needs_attention && <AlertTriangle size={14} className="text-amber-500" title="Needs attention" />}</div>
                {p.external_id && <div className="text-xs text-slate-400">{p.external_id}</div>}</td>
              <td className="td">{p.display_name || <span className="text-slate-400">Not Available</span>}</td>
              <td className="td">{p.age ?? <Dash />}</td>
              <td className="td">{p.sex === 'M' ? 'Male' : p.sex === 'F' ? 'Female' : <Dash />}</td>
              <td className="td font-semibold">{p.latest_hba1c != null ? `${fmtNum(p.latest_hba1c)}%` : <Dash />}</td>
              <td className="td">{p.latest_ppbs != null ? fmtNum(p.latest_ppbs, 0) : <Dash />}</td>
              <td className="td">{p.latest_glucose ? <span className={`font-semibold ${glucoseTone(p.latest_glucose.value)}`}>{fmtNum(p.latest_glucose.value, 0)}{p.latest_glucose.source === 'lab' && <span className="ml-1 text-[10px] font-medium text-slate-400">lab</span>}</span> : <Dash />}</td>
              <td className="td">{p.height_cm != null ? fmtNum(p.height_cm) : <Dash />}</td>
              <td className="td">{p.weight_kg != null ? fmtNum(p.weight_kg) : <Dash />}</td>
              <td className="td">{p.bmi != null ? fmtNum(p.bmi) : <Dash />}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PatientList() {
  const [sp, setSp] = useSearchParams()
  const [search, setSearch] = useState(sp.get('search') || '')
  const [q, setQ] = useState(search)
  const [attention, setAttention] = useState(sp.get('attention') === '1')
  const [page, setPage] = useState(1)
  useEffect(() => { const t = setTimeout(() => { setQ(search); setPage(1) }, 300); return () => clearTimeout(t) }, [search])
  const st = useFetch(() => api.get('/api/doctor/patients', { params: { search: q, attention, page, page_size: 20 } }).then((r) => r.data), [q, attention, page])
  const toggle = (v) => { setAttention(v); setPage(1); const n = new URLSearchParams(sp); v ? n.set('attention', '1') : n.delete('attention'); setSp(n, { replace: true }) }
  return (
    <Card>
      <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 p-4">
        <div className="relative min-w-[240px] flex-1"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input className="input !pl-9" placeholder="Search by patient ID or name" value={search} onChange={(e) => setSearch(e.target.value)} /></div>
        <div className="inline-flex gap-1 rounded-xl bg-slate-100 p-1">
          {[[false, 'All patients'], [true, 'Needs attention']].map(([v, l]) => (
            <button key={l} onClick={() => toggle(v)} className={`rounded-lg px-3.5 py-1.5 text-sm font-semibold transition ${attention === v ? 'bg-white text-navy-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}>{l}</button>
          ))}
        </div>
      </div>
      {st.loading && !st.data ? <Loading /> : st.error ? <div className="p-4"><ErrorBox message={st.error} onRetry={st.reload} /></div> : (
        <div className={st.loading ? 'opacity-60 transition' : 'transition'}>
          <PatientTable items={st.data.items} />
          <Pagination page={page} pageSize={20} total={st.data.total} onPage={setPage} />
        </div>
      )}
    </Card>
  )
}

function Unassigned() {
  const st = useFetch(() => api.get('/api/doctor/patients/unassigned').then((r) => r.data.items), [])
  const [err, setErr] = useState('')
  const assign = async (id) => { try { setErr(''); await api.post(`/api/doctor/patients/${id}/assign`); st.reload() } catch (e) { setErr(errMsg(e)) } }
  return (
    <Card>
      {err && <div className="m-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      <Async state={st}>{(items) => items.length === 0 ? <Empty title="No patients are waiting" hint="Newly registered patients appear here until you assign them." /> : (
        <table className="w-full text-left"><thead className="bg-slate-50"><tr>{['Patient ID', 'Name', 'Gender', 'Registered', ''].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-100">{items.map((p) => (
            <tr key={p.id}><td className="td font-semibold text-navy-900">{p.patient_code}</td><td className="td">{p.display_name || '—'}</td>
              <td className="td">{p.sex === 'M' ? 'Male' : p.sex === 'F' ? 'Female' : '—'}</td><td className="td text-slate-500">{fmtDate(p.created_at)}</td>
              <td className="td text-right"><button className="btn-primary !py-1.5" onClick={() => assign(p.id)}><UserCheck size={14} />Assign to me</button></td></tr>
          ))}</tbody></table>)}</Async>
    </Card>
  )
}

export default function PatientsPage() {
  const [sp, setSp] = useSearchParams()
  const tab = sp.get('tab') === 'unassigned' ? 'unassigned' : 'patients'
  const waiting = useFetch(() => api.get('/api/doctor/patients/unassigned').then((r) => r.data.items.length), [tab])
  return (
    <>
      <PageHeader title="Patient Review & Alerts" />
      <div className="mb-5 flex gap-1 border-b border-slate-200">
        {[['patients', 'Patients'], ['unassigned', 'Awaiting assignment']].map(([k, l]) => (
          <button key={k} onClick={() => setSp(k === 'patients' ? {} : { tab: k })}
            className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold transition ${tab === k ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>
            {l}{k === 'unassigned' && waiting.data > 0 && <span className="rounded-full bg-rose-100 px-1.5 text-[11px] font-bold text-rose-700">{waiting.data}</span>}</button>
        ))}
      </div>
      {tab === 'patients' ? <PatientList /> : <Unassigned />}
    </>
  )
}
