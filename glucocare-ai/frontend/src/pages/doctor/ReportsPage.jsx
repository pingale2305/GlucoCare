import api from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { Async, Card, PageHeader } from '../../components/ui'
import ReportTable from '../../components/ReportTable'

export default function ReportsPage() {
  const st = useFetch(() => api.get('/api/doctor/reports').then((r) => r.data.items), [])
  return (
    <>
      <PageHeader title="Report Management" />
      <Card><Async state={st}>{(items) => <ReportTable items={items} showPatient />}</Async></Card>
    </>
  )
}
