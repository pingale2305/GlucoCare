import { useState } from 'react'
import { CalendarCheck, CalendarDays, Clock, Video } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import api, { errMsg } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { Async, Card, CardHeader, Empty, Field, PageHeader, Spinner } from '../../components/ui'
import SlotPicker from '../../components/SlotPicker'
import { JoinButton, StatusBadge, fmtSlot, isOpen, isPast } from '../../components/AppointmentBits'

export default function PatientAppointments() {
  const pid = useAuth().user.patient_id
  const st = useFetch(() => api.get(`/api/patients/${pid}/appointments`).then((r) => r.data), [pid])
  const [slot, setSlot] = useState(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState({ text: '', ok: false })
  const [tick, setTick] = useState(0)

  const book = async () => {
    setBusy(true); setMsg({ text: '' })
    try {
      await api.post(`/api/patients/${pid}/appointments`, { start_at: slot, reason: reason.trim() || null })
      setMsg({ text: 'Request sent. You will be notified when the doctor responds.', ok: true }); setSlot(null); setReason(''); setTick((t) => t + 1); st.reload()
    } catch (e) { setMsg({ text: errMsg(e) }); setTick((t) => t + 1) } finally { setBusy(false) }
  }
  const act = async (id, path, body) => {
    setMsg({ text: '' })
    try { await api.post(`/api/patients/${pid}/appointments/${id}/${path}`, body); setTick((t) => t + 1); st.reload() } catch (e) { setMsg({ text: errMsg(e) }) }
  }

  return (
    <>
      <PageHeader title="Appointments" />
      <div className="space-y-6">
        <Card>
          <CardHeader title="Book a 40-minute Zoom appointment" icon={CalendarDays} subtitle={st.data?.doctor_name ? `With ${st.data.doctor_name}` : undefined} />
          <div className="p-5">
            {st.data && !st.data.has_doctor ? (
              <Empty title="Waiting for your doctor" hint="Appointments open as soon as your doctor accepts your registration." />
            ) : (
              <div className="space-y-5">
                <SlotPicker value={slot} onChange={setSlot} refreshKey={tick} fetchSlots={(day) => api.get(`/api/patients/${pid}/appointments/slots`, { params: { day } }).then((r) => r.data.slots)} />
                <div className="grid gap-4 border-t border-slate-100 pt-5 md:grid-cols-[1fr_auto] md:items-end">
                  <Field label="Reason (optional)"><input className="input" maxLength={300} placeholder="e.g. Discuss latest HbA1c" value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
                  <button className="btn-primary !py-2.5" disabled={!slot || busy} onClick={book}>{busy ? <Spinner size={16} /> : <CalendarCheck size={16} />}{slot ? `Request ${fmtSlot(slot)}` : 'Select a time'}</button>
                </div>
              </div>
            )}
            {msg.text && <div role="alert" className={`mt-4 rounded-xl px-3 py-2.5 text-sm ${msg.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{msg.text}</div>}
          </div>
        </Card>

        <Card>
          <CardHeader title="My appointments" icon={Clock} />
          <Async state={st}>{(d) => d.items.length === 0 ? <Empty title="No appointments yet" /> : (
            <ul className="divide-y divide-slate-100">
              {d.items.map((a) => (
                <li key={a.id} className="flex flex-wrap items-center gap-4 px-5 py-4">
                  <div className="min-w-[200px] flex-1">
                    <div className="flex items-center gap-2"><span className="font-semibold text-navy-900">{fmtSlot(a.start_at)}</span><StatusBadge status={a.status} /></div>
                    <div className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-500"><Video size={12} />{a.duration_min} min on Zoom · {a.doctor_name}{a.reason ? ` · ${a.reason}` : ''}</div>
                    {a.status === 'reschedule_proposed' && <div className="mt-1 text-xs text-sky-700">The doctor proposed this new time. Please confirm.</div>}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {a.status === 'accepted' && !isPast(a) && a.zoom_url && <JoinButton url={a.zoom_url} />}
                    {a.status === 'reschedule_proposed' && <>
                      <button className="btn-primary !px-3 !py-1.5" onClick={() => act(a.id, 'respond', { action: 'accept' })}>Accept new time</button>
                      <button className="btn-ghost !px-3 !py-1.5" onClick={() => act(a.id, 'respond', { action: 'decline' })}>Decline</button></>}
                    {isOpen(a) && !isPast(a) && a.status !== 'reschedule_proposed' && <button className="btn-ghost !px-3 !py-1.5" onClick={() => act(a.id, 'cancel')}>Cancel</button>}
                  </div>
                </li>
              ))}
            </ul>)}</Async>
        </Card>
      </div>
    </>
  )
}
