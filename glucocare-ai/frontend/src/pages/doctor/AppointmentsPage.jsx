import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, CalendarClock, CalendarCheck, Video, X } from 'lucide-react'
import api, { errMsg } from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { Async, Card, CardHeader, Empty, Field, Modal, PageHeader, Spinner } from '../../components/ui'
import SlotPicker from '../../components/SlotPicker'
import { JoinButton, StatusBadge, fmtSlot, isOpen, isPast } from '../../components/AppointmentBits'
import { nameOrId } from '../../utils/format'

function Row({ a, children }) {
  return (
    <li className="flex flex-wrap items-center gap-4 px-5 py-4">
      <div className="min-w-[220px] flex-1">
        <div className="flex flex-wrap items-center gap-2"><Link to={`/doctor/review/${a.patient_id}`} className="font-semibold text-navy-900 hover:text-brand-700">{nameOrId(a)}</Link><span className="text-xs text-slate-400">{a.patient_code}</span><StatusBadge status={a.status} /></div>
        <div className="mt-0.5 text-sm text-slate-600">{fmtSlot(a.start_at)} · {a.duration_min} min{a.reason ? ` · ${a.reason}` : ''}</div>
        {a.requested_start_at && a.status === 'reschedule_proposed' && <div className="text-xs text-slate-400">Originally requested {fmtSlot(a.requested_start_at)}</div>}
      </div>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </li>
  )
}

export default function AppointmentsPage() {
  const st = useFetch(() => api.get('/api/doctor/appointments').then((r) => r.data), [])
  const [err, setErr] = useState('')
  const [accepting, setAccepting] = useState(null)   // appointment being accepted
  const [moving, setMoving] = useState(null)         // appointment being moved
  const [zoom, setZoom] = useState('')
  const [slot, setSlot] = useState(null)
  const [busy, setBusy] = useState(false)
  const [tick, setTick] = useState(0)

  const run = async (fn) => { setBusy(true); setErr(''); try { await fn(); setAccepting(null); setMoving(null); setSlot(null); setTick((t) => t + 1); st.reload() } catch (e) { setErr(errMsg(e)) } finally { setBusy(false) } }
  const openAccept = (a) => { setZoom(st.data.last_zoom_url || ''); setErr(''); setAccepting(a) }
  const openMove = (a) => { setZoom(a.zoom_url || st.data.last_zoom_url || ''); setSlot(null); setErr(''); setMoving(a) }

  return (
    <>
      <PageHeader title="Appointments" />
      <Async state={st}>{(d) => {
        const pending = d.items.filter((a) => a.status === 'pending' && !isPast(a)).reverse()
        const upcoming = d.items.filter((a) => a.status === 'accepted' && !isPast(a)).reverse()
        const waiting = d.items.filter((a) => a.status === 'reschedule_proposed' && !isPast(a)).reverse()
        const history = d.items.filter((a) => !(isOpen(a) && !isPast(a)))
        return (
          <div className="space-y-6">
            {err && !accepting && !moving && <div role="alert" className="rounded-xl bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{err}</div>}
            <Card><CardHeader title={`Requests (${pending.length})`} icon={CalendarClock} />
              {pending.length === 0 ? <Empty title="No pending requests" /> : <ul className="divide-y divide-slate-100">{pending.map((a) => (
                <Row key={a.id} a={a}>
                  <button className="btn-primary !px-3 !py-1.5" onClick={() => openAccept(a)}><Check size={14} />Accept</button>
                  <button className="btn-ghost !px-3 !py-1.5" onClick={() => openMove(a)}><CalendarClock size={14} />Suggest new date</button>
                  <button className="btn-ghost !px-3 !py-1.5" onClick={() => run(() => api.post(`/api/doctor/appointments/${a.id}/cancel`))}><X size={14} />Decline</button>
                </Row>))}</ul>}
            </Card>
            <Card><CardHeader title={`Upcoming Zoom calls (${upcoming.length})`} icon={Video} />
              {upcoming.length === 0 ? <Empty title="No confirmed appointments" /> : <ul className="divide-y divide-slate-100">{upcoming.map((a) => (
                <Row key={a.id} a={a}>
                  {a.zoom_url && <JoinButton url={a.zoom_url} />}
                  <button className="btn-ghost !px-3 !py-1.5" onClick={() => openMove(a)}>Reschedule</button>
                  <button className="btn-ghost !px-3 !py-1.5" onClick={() => run(() => api.post(`/api/doctor/appointments/${a.id}/cancel`))}>Cancel</button>
                </Row>))}</ul>}
            </Card>
            {waiting.length > 0 && <Card><CardHeader title="Waiting for the patient to confirm a new time" />
              <ul className="divide-y divide-slate-100">{waiting.map((a) => <Row key={a.id} a={a} />)}</ul></Card>}
            {history.length > 0 && <Card><CardHeader title="Past and closed" />
              <ul className="max-h-96 divide-y divide-slate-100 overflow-auto">{history.map((a) => <Row key={a.id} a={a} />)}</ul></Card>}

            <Modal open={!!accepting} onClose={() => setAccepting(null)} title="Confirm appointment">
              {accepting && <div className="space-y-4">
                <p className="text-sm text-slate-600"><b>{nameOrId(accepting)}</b> · {fmtSlot(accepting.start_at)} · 40 minutes</p>
                <Field label="Zoom meeting link" hint="Paste your Zoom meeting link. The patient sees it after you confirm."><input className="input" placeholder="https://zoom.us/j/…" value={zoom} onChange={(e) => setZoom(e.target.value)} /></Field>
                {err && <div role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
                <button className="btn-primary w-full" disabled={busy || !zoom.trim()} onClick={() => run(() => api.post(`/api/doctor/appointments/${accepting.id}/accept`, { zoom_url: zoom.trim() }))}>{busy ? <Spinner size={16} /> : <CalendarCheck size={16} />}Confirm appointment</button>
              </div>}
            </Modal>
            <Modal open={!!moving} onClose={() => setMoving(null)} title="Suggest a new date" wide>
              {moving && <div className="space-y-4">
                <p className="text-sm text-slate-600"><b>{nameOrId(moving)}</b> · currently {fmtSlot(moving.start_at)}</p>
                <SlotPicker value={slot} onChange={setSlot} refreshKey={tick} fetchSlots={(day) => api.get('/api/doctor/appointments/slots', { params: { day } }).then((r) => r.data.slots)} />
                <Field label="Zoom meeting link"><input className="input" placeholder="https://zoom.us/j/…" value={zoom} onChange={(e) => setZoom(e.target.value)} /></Field>
                {err && <div role="alert" className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
                <button className="btn-primary w-full" disabled={busy || !slot || !zoom.trim()} onClick={() => run(() => api.post(`/api/doctor/appointments/${moving.id}/propose`, { start_at: slot, zoom_url: zoom.trim() }))}>{busy ? <Spinner size={16} /> : null}Send new time to patient</button>
              </div>}
            </Modal>
          </div>
        )
      }}</Async>
    </>
  )
}
