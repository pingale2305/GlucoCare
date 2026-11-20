import { useState } from 'react'
import { MessageSquareText, Pencil } from 'lucide-react'
import api from '../../services/api'
import useFetch from '../../hooks/useFetch'
import { Async, Card, CardHeader, Empty, PageHeader } from '../../components/ui'
import SuggestionForm from '../../components/SuggestionForm'
import { fmtDate, nameOrId } from '../../utils/format'
import { Link } from 'react-router-dom'

export default function SuggestionsPage() {
  const st = useFetch(() => api.get('/api/doctor/suggestions').then((r) => r.data.items), [])
  const [editing, setEditing] = useState(null)
  return (
    <>
      <PageHeader title="Doctor Suggestions" />
      <div className="grid gap-6 xl:grid-cols-[440px_1fr]">
        <Card className="self-start">
          <CardHeader title={editing ? 'Edit suggestion' : 'New suggestion'} icon={MessageSquareText}
            subtitle={editing ? nameOrId(editing) : undefined} />
          <div className="p-5"><SuggestionForm editing={editing} onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); st.reload() }} /></div>
        </Card>
        <Card><CardHeader title="Previous suggestions" />
          <Async state={st}>{(items) => items.length === 0 ? <Empty title="No suggestions yet" /> : (
            <ul className="divide-y divide-slate-100">
              {items.map((s) => (
                <li key={s.id} className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div><Link to={`/doctor/review/${s.patient_id}`} className="font-semibold text-navy-900 hover:text-brand-700">{nameOrId(s)}</Link><span className="ml-2 text-xs text-slate-400">{s.patient_code} · {fmtDate(s.suggestion_date)}</span></div>
                    <button className="btn-ghost !px-3 !py-1.5" onClick={() => { setEditing(s); window.scrollTo({ top: 0, behavior: 'smooth' }) }}><Pencil size={13} />Edit</button>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{s.content}</p>
                </li>
              ))}
            </ul>)}</Async></Card>
      </div>
    </>
  )
}
