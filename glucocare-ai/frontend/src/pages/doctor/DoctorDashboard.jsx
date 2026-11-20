import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertTriangle, ArrowRight, CalendarClock, Check, Droplet, UserPlus, Users } from 'lucide-react'
import api, { errMsg } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { Async, Card, CardHeader, Empty, PageHeader, SeverityBadge, Stat } from '../../components/ui'
import { PatientTable } from './PatientsPage'
import { CONTEXT, fmtDateTime, glucoseTone } from '../../utils/format'

export default function DoctorDashboard() {
  const navigate = useNavigate()
  const st = useFetch(() => api.get('/api/doctor/dashboard').then((r) => r.data), [])
  const [err, setErr] = useState('')
  const review = async (id) => { try { setErr(''); await api.post(`/api/doctor/alerts/${id}/review`, {}); st.reload() } catch (e) { setErr(errMsg(e)) } }
  return (
    <>
      <PageHeader title="Dashboard" />
      <Async state={st}>{(d) => (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <Stat label="Total patients" value={d.total_patients.toLocaleString()} icon={Users} tone="teal" onClick={() => navigate('/doctor/patients')} />
            <Stat label="Patients requiring attention" value={d.requiring_attention.toLocaleString()} icon={AlertTriangle} tone={d.requiring_attention ? 'amber' : 'green'} onClick={() => navigate('/doctor/patients?attention=1')} />
          </div>
          {d.awaiting_assignment > 0 && (
            <Link to="/doctor/patients?tab=unassigned" className="flex items-center justify-between rounded-2xl border border-brand-200 bg-brand-50 px-5 py-3.5 text-sm font-medium text-brand-900 transition hover:bg-brand-100">
              <span className="flex items-center gap-2.5"><UserPlus size={17} />{d.awaiting_assignment} new {d.awaiting_assignment === 1 ? 'patient is' : 'patients are'} waiting to be assigned</span><ArrowRight size={16} />
            </Link>
          )}
          {d.pending_appointments > 0 && (
            <Link to="/doctor/appointments" className="flex items-center justify-between rounded-2xl border border-sky-200 bg-sky-50 px-5 py-3.5 text-sm font-medium text-sky-900 transition hover:bg-sky-100">
              <span className="flex items-center gap-2.5"><CalendarClock size={17} />{d.pending_appointments} appointment {d.pending_appointments === 1 ? 'request needs' : 'requests need'} your response</span><ArrowRight size={16} />
            </Link>
          )}
          <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
            <Card>
              <CardHeader title="Important health alerts" icon={AlertTriangle} />
              {err && <div className="m-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
              {d.alerts.length === 0 ? <Empty title="No alerts need attention" /> : (
                <ul className="divide-y divide-slate-100">
                  {d.alerts.map((a) => (
                    <li key={a.id} className="flex items-start gap-3 px-5 py-3.5">
                      <SeverityBadge severity={a.severity} />
                      <div className="min-w-0 flex-1"><Link to={`/doctor/review/${a.patient_id}`} className="text-sm font-semibold text-navy-900 hover:text-brand-700">{a.patient}</Link>
                        <div className="text-sm text-slate-600">{a.reason}</div></div>
                      <button className="btn-ghost !px-2.5 !py-1.5 text-xs" onClick={() => review(a.id)} title="Mark as reviewed"><Check size={13} />Reviewed</button>
                    </li>
                  ))}
                </ul>)}
            </Card>
            <Card>
              <CardHeader title="Recent glucose readings" icon={Droplet} />
              {d.recent_readings.length === 0 ? <Empty title="No readings entered yet" /> : (
                <ul className="divide-y divide-slate-100">
                  {d.recent_readings.map((r) => (
                    <li key={r.id}><Link to={`/doctor/review/${r.patient_id}`} className="flex items-center justify-between gap-3 px-5 py-3 transition hover:bg-slate-50">
                      <div className="min-w-0"><div className="truncate text-sm font-semibold text-navy-900">{r.patient}</div><div className="text-xs text-slate-500">{CONTEXT[r.context]} · {fmtDateTime(r.measured_at)}</div></div>
                      <div className={`text-lg font-bold ${glucoseTone(r.value_mg_dl)}`}>{r.value_mg_dl}<span className="ml-1 text-xs font-medium text-slate-400">mg/dL</span></div></Link></li>
                  ))}
                </ul>)}
            </Card>
          </div>
          <Card>
            <CardHeader title="Recent patient records" action={<Link to="/doctor/patients" className="text-sm font-semibold text-brand-700 hover:underline">View all</Link>} />
            <PatientTable items={d.recent_patients} />
          </Card>
        </div>
      )}</Async>
    </>
  )
}
