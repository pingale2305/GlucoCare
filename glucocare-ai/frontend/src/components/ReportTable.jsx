import { useState } from 'react'
import { Download, ExternalLink, FileText } from 'lucide-react'
import { downloadFile, errMsg, openFile } from '../services/api'
import { fmtDate, fmtDateTime } from '../utils/format'
import { Badge, Empty } from './ui'

const TYPE = { lab_report: 'Lab report', prescription: 'Prescription', scan: 'Scan', other: 'Other' }
const kb = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`)

/** Report list with Open / Download. showPatient adds the uploading patient column (doctor view). */
export default function ReportTable({ items, showPatient = false }) {
  const [err, setErr] = useState('')
  const act = async (fn) => { try { setErr(''); await fn() } catch (e) { setErr(errMsg(e)) } }
  if (!items.length) return <Empty title="No reports uploaded" />
  return (
    <div>
      {err && <div className="m-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{err}</div>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left">
          <thead className="bg-slate-50"><tr>
            <th className="th">Report</th>{showPatient && <th className="th">Patient</th>}<th className="th">Type</th><th className="th">Report date</th><th className="th">Uploaded</th><th className="th text-right">Actions</th>
          </tr></thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((r) => {
              const url = `/api/patients/${r.patient_id}/reports/${r.id}/download`
              return (
                <tr key={r.id} className="transition hover:bg-slate-50">
                  <td className="td"><div className="flex items-center gap-2.5"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-700"><FileText size={15} /></span>
                    <div className="min-w-0"><div className="truncate font-medium text-slate-800">{r.title}</div><div className="truncate text-xs text-slate-400">{r.original_filename} · {kb(r.size_bytes)}</div></div></div></td>
                  {showPatient && <td className="td"><div className="font-medium">{r.patient_name || r.patient_code}</div><div className="text-xs text-slate-400">{r.patient_code}</div></td>}
                  <td className="td"><Badge tone="teal">{TYPE[r.report_type] || 'Other'}</Badge></td>
                  <td className="td text-slate-600">{fmtDate(r.report_date)}</td>
                  <td className="td text-slate-600">{fmtDateTime(r.created_at)}</td>
                  <td className="td"><div className="flex justify-end gap-2">
                    <button className="btn-ghost !px-3 !py-1.5" onClick={() => act(() => openFile(url, r.original_filename))}><ExternalLink size={14} />Open</button>
                    <button className="btn-ghost !px-3 !py-1.5" onClick={() => act(() => downloadFile(url, r.original_filename))}><Download size={14} />Download</button>
                  </div></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
