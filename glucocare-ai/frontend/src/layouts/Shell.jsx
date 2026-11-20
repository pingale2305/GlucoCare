import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Bell, Droplet, LogOut, Menu, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import useFetch from '../hooks/useFetch'
import NotificationPanel from '../components/NotificationPanel'
import { initials } from '../utils/format'

function Bell_({ role }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const n = useFetch(() => api.get('/api/notifications').then((r) => r.data), [])
  useEffect(() => { const t = setInterval(n.reload, 30000); return () => clearInterval(t) }, [n.reload])
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h)
  }, [])
  const unread = n.data?.unread || 0
  return (
    <div className="relative" ref={ref}>
      <button aria-label="Notifications" className="relative rounded-xl p-2.5 text-slate-600 transition hover:bg-slate-100"
        onClick={() => { if (role === 'doctor') navigate('/doctor/notifications'); else { setOpen((o) => !o); n.reload() } }}>
        <Bell size={19} />
        {unread > 0 && <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">{unread > 9 ? '9+' : unread}</span>}
      </button>
      {open && role === 'patient' && (
        <div className="card absolute right-0 top-12 z-40 w-[22rem] max-w-[90vw] animate-fadeUp overflow-hidden">
          <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-800">Notifications</div>
          {n.data ? <NotificationPanel data={n.data} reload={n.reload} compact onNavigate={() => setOpen(false)} /> : <div className="p-6 text-center text-sm text-slate-400">Loading…</div>}
        </div>
      )}
    </div>
  )
}

/** Sidebar shell shared by the doctor and patient portals. */
export default function Shell({ nav, title }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  return (
    <div className="min-h-screen lg:pl-64">
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-navy-900 text-slate-300 transition-transform duration-200 ${open ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        <div className="flex h-16 items-center justify-between px-5">
          <div className="flex items-center gap-2.5 text-white">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-500"><Droplet size={18} /></span>
            <div><div className="font-extrabold leading-none">GlucoCare</div><div className="mt-1 text-[11px] text-brand-300">{title}</div></div>
          </div>
          <button className="lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu"><X size={18} /></button>
        </div>
        <nav className="mt-4 flex-1 space-y-1 px-3">
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} onClick={() => setOpen(false)}
              className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition ${isActive ? 'bg-brand-500 text-white shadow-sm' : 'text-slate-300 hover:bg-white/5 hover:text-white'}`}>
              <n.icon size={17} />{n.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/10 p-3">
          <div className="mb-2 flex items-center gap-3 rounded-xl bg-white/5 p-3">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-500 text-xs font-bold text-white">{initials(user?.full_name)}</div>
            <div className="min-w-0"><div className="truncate text-sm font-semibold text-white">{user?.full_name}</div><div className="truncate text-xs text-slate-400">{user?.email}</div></div>
          </div>
          <button onClick={() => { logout(); navigate('/login') }} className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-300 transition hover:bg-white/5 hover:text-white"><LogOut size={16} />Sign out</button>
        </div>
      </aside>
      {open && <div className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" onClick={() => setOpen(false)} />}

      <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:justify-end lg:px-8">
        <button className="rounded-lg p-2 hover:bg-slate-100 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={20} /></button>
        <Bell_ role={user?.role} />
      </header>
      <main className="mx-auto max-w-[1400px] p-4 lg:p-8"><Outlet /></main>
    </div>
  )
}
