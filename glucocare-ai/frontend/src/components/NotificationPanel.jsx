import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCheck, Circle, CircleDot } from 'lucide-react'
import api, { errMsg } from '../services/api'
import { fmtDateTime } from '../utils/format'
import { Empty } from './ui'

/** Notification list with read / unread toggle. Used by the doctor page and the patient bell. */
export default function NotificationPanel({ data, reload, compact = false, onNavigate }) {
  const navigate = useNavigate()
  const [err, setErr] = useState('')
  const run = async (fn) => { try { setErr(''); await fn(); reload() } catch (e) { setErr(errMsg(e)) } }
  const items = data?.items || []
  return (
    <div>
      <div className="flex items-center justify-between px-4 py-3">
        <div className="text-sm text-slate-500">{data?.unread ? `${data.unread} unread` : 'All caught up'}</div>
        {data?.unread > 0 && <button className="flex items-center gap-1.5 text-xs font-semibold text-brand-700 hover:underline" onClick={() => run(() => api.post('/api/notifications/read-all'))}><CheckCheck size={14} />Mark all as read</button>}
      </div>
      {err && <div className="px-4 pb-2 text-xs text-rose-600">{err}</div>}
      {items.length === 0 ? <Empty title="No notifications" /> : (
        <ul className={`divide-y divide-slate-100 ${compact ? 'max-h-96 overflow-auto' : ''}`}>
          {items.map((n) => (
            <li key={n.id} className={`flex items-start gap-3 px-4 py-3 ${n.is_read ? '' : 'bg-brand-50/50'}`}>
              <button title={n.is_read ? 'Mark as unread' : 'Mark as read'} className="mt-0.5 text-brand-600"
                onClick={() => run(() => api.post(`/api/notifications/${n.id}/${n.is_read ? 'unread' : 'read'}`))}>
                {n.is_read ? <Circle size={16} className="text-slate-300" /> : <CircleDot size={16} />}
              </button>
              <button className="min-w-0 flex-1 text-left" onClick={async () => {
                if (!n.is_read) await run(() => api.post(`/api/notifications/${n.id}/read`))
                if (n.link) { onNavigate?.(); navigate(n.link) }
              }}>
                <div className={`text-sm ${n.is_read ? 'text-slate-600' : 'font-semibold text-slate-900'}`}>{n.title}</div>
                <div className="mt-0.5 line-clamp-2 text-xs text-slate-500">{n.message}</div>
                <div className="mt-1 text-[11px] text-slate-400">{fmtDateTime(n.created_at)}</div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
