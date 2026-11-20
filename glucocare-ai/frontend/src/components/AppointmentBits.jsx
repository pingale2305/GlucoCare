import { Video } from 'lucide-react'
import { Badge } from './ui'

export const APPT_STATUS = {
  pending: ['Waiting for doctor', 'amber'], accepted: ['Confirmed', 'green'], reschedule_proposed: ['New time proposed', 'blue'],
  declined: ['Declined', 'slate'], cancelled: ['Cancelled', 'slate'],
}
export const StatusBadge = ({ status }) => { const [l, t] = APPT_STATUS[status] || [status, 'slate']; return <Badge tone={t}>{l}</Badge> }

export const isOpen = (a) => ['pending', 'accepted', 'reschedule_proposed'].includes(a.status)
export const isPast = (a) => new Date(a.start_at).getTime() + (a.duration_min || 40) * 60000 < Date.now()

export const fmtSlot = (iso) => new Date(iso).toLocaleString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', hour: 'numeric', minute: '2-digit', hour12: true })

export const JoinButton = ({ url }) => (
  <a href={url} target="_blank" rel="noopener noreferrer" className="btn-primary !px-3 !py-1.5"><Video size={14} />Join Zoom</a>
)
