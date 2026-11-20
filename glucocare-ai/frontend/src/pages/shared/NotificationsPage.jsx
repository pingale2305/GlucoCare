import api from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { Async, Card, PageHeader } from '../../components/ui'
import NotificationPanel from '../../components/NotificationPanel'

export default function NotificationsPage() {
  const st = useFetch(() => api.get('/api/notifications').then((r) => r.data), [])
  return (
    <>
      <PageHeader title="Notifications" />
      <Card className="max-w-3xl"><Async state={st}>{(d) => <NotificationPanel data={d} reload={st.reload} />}</Async></Card>
    </>
  )
}
