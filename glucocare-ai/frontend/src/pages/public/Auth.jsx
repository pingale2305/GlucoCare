import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { CalendarDays, CheckCircle2, Droplet, Eye, FileText, EyeOff, Lock, Mail, Stethoscope, User } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import api, { errMsg } from '../../services/api'
import { bmiBand, bmiOf } from '../../utils/format'
import { Field, Spinner } from '../../components/ui'

function Pulse() {
  // one drawn-in glucose trace; the only moving element on the page
  return (
    <svg viewBox="0 0 520 140" className="w-full" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="trace" x1="0" x2="1"><stop offset="0" stopColor="#2dd4bf" stopOpacity="0" /><stop offset=".25" stopColor="#2dd4bf" /><stop offset="1" stopColor="#99f6e4" /></linearGradient>
        <linearGradient id="fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#2dd4bf" stopOpacity=".22" /><stop offset="1" stopColor="#2dd4bf" stopOpacity="0" /></linearGradient>
      </defs>
      <path d="M0 96 C40 96 52 70 84 74 S128 112 164 92 S214 38 252 50 S304 118 344 88 S400 30 440 46 S492 70 520 52 V140 H0Z" fill="url(#fill)" />
      <path className="trace-line" d="M0 96 C40 96 52 70 84 74 S128 112 164 92 S214 38 252 50 S304 118 344 88 S400 30 440 46 S492 70 520 52" stroke="url(#trace)" strokeWidth="3" strokeLinecap="round" />
      <circle cx="520" cy="52" r="5" fill="#99f6e4" /><circle cx="520" cy="52" r="11" fill="#2dd4bf" opacity=".25" />
    </svg>
  )
}

function Frame({ title, subtitle, children }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <div className="relative hidden overflow-hidden bg-navy-950 lg:block">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(20,184,166,.30),transparent_45%),radial-gradient(circle_at_90%_90%,rgba(45,212,191,.16),transparent_40%)]" />
        <div className="absolute inset-0 opacity-[.07] [background-image:linear-gradient(#fff_1px,transparent_1px),linear-gradient(90deg,#fff_1px,transparent_1px)] [background-size:44px_44px]" />
        <div className="relative flex h-full flex-col justify-between p-14 text-white">
          <div className="flex items-center gap-3">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-brand-400 to-brand-600 shadow-lg shadow-brand-900/40"><Droplet size={24} /></span>
            <div><div className="text-2xl font-extrabold leading-none tracking-tight">GlucoCare<span className="text-brand-300"> </span></div></div>
          </div>
          <div>
            <Pulse />
          <h2 className="mt-7 max-w-md text-4xl font-extrabold leading-tight tracking-tight">
 Small steps, Stronger you. <span className="text-brand-300">Control it. Track it. Beat it.</span>
</h2>
          </div>
          <div className="text-xs text-slate-500">Clinical decision-support. </div>
        </div>
      </div>
      <div className="flex items-center justify-center bg-[linear-gradient(180deg,#f8fafc,#eef6f6)] px-5 py-10">
        <div className="w-full max-w-md animate-fadeUp rounded-3xl border border-slate-100 bg-white p-8 shadow-[0_20px_60px_-20px_rgba(11,31,63,.25)] sm:p-10">
          <div className="mb-7 flex items-center gap-2.5 lg:hidden"><span className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 text-white"><Droplet size={20} /></span><span className="text-lg font-extrabold text-navy-900">GlucoCare AI</span></div>
          <h1 className="text-3xl font-extrabold tracking-tight text-navy-900">{title}</h1>
          <p className="mt-1.5 text-sm text-slate-500">{subtitle}</p>
          <div className="mt-7">{children}</div>
        </div>
      </div>
    </div>
  )
}

function PasswordInput({ id, reg, error, autoComplete }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
      <input id={id} type={show ? 'text' : 'password'} autoComplete={autoComplete} className={`input !py-2.5 !pl-9 !pr-10 ${error ? '!border-rose-300' : ''}`} {...reg} />
      <button type="button" aria-label={show ? 'Hide password' : 'Show password'} onClick={() => setShow((s) => !s)}
        className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700">{show ? <EyeOff size={16} /> : <Eye size={16} />}</button>
    </div>
  )
}

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [sp] = useSearchParams()
  const [role, setRole] = useState('patient')
  const [error, setError] = useState(sp.get('expired') ? 'Your session expired. Please sign in again.' : '')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm()
  const submit = async (v) => {
    setError('')
    try { const u = await login(v.email.trim(), v.password, role); navigate(`/${u.role}`, { replace: true }) }
    catch (e) { setError(errMsg(e)) }
  }
  return (
    <Frame title="Sign in" subtitle="Choose your role and enter your account details.">
      <div className="mb-5 grid grid-cols-2 gap-1 rounded-xl bg-slate-100 p-1">
        {[['patient', 'Patient', User], ['doctor', 'Doctor', Stethoscope]].map(([k, label, Icon]) => (
          <button key={k} type="button" onClick={() => setRole(k)}
            className={`flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold transition ${role === k ? 'bg-white text-navy-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}><Icon size={15} />{label}</button>
        ))}
      </div>
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        <Field label="Email" error={errors.email?.message}>
          <div className="relative"><Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input type="email" autoComplete="username" className="input !py-2.5 !pl-9" {...register('email', { required: 'Enter your email' })} /></div>
        </Field>
        <Field label="Password" error={errors.password?.message}>
          <PasswordInput autoComplete="current-password" error={errors.password} reg={register('password', { required: 'Enter your password' })} />
        </Field>
        {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</div>}
        <button className="btn-primary w-full !bg-navy-900 !py-2.5 hover:!bg-navy-800" disabled={isSubmitting}>{isSubmitting ? <Spinner size={16} /> : null}Sign in</button>
      </form>
      {role === 'patient' && (
  <p className="mt-6 text-center text-sm text-slate-500">New patient? <Link to="/register" className="font-semibold text-brand-700 hover:underline">Create an account</Link></p>
)}
    </Frame>
  )
}

export function Register() {
  const [done, setDone] = useState(null)
  const [error, setError] = useState('')
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm({ defaultValues: { sex: '' } })
  const bmi = bmiOf(+watch('height_cm'), +watch('weight_kg'))
  const submit = async (v) => {
    setError('')
    const body = {
      full_name: v.full_name.trim(), email: v.email.trim(), password: v.password, sex: v.sex || null,
      date_of_birth: v.date_of_birth || null, phone: v.phone?.trim() || null,
      height_cm: v.height_cm ? +v.height_cm : null, weight_kg: v.weight_kg ? +v.weight_kg : null,
    }
    try { const { data } = await api.post('/api/auth/register', body); setDone(data.patient_code) }
    catch (e) { setError(errMsg(e)) }
  }
  if (done) return (
    <Frame title="Account created" subtitle="Your doctor will assign you after registration.">
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-center">
        <CheckCircle2 className="mx-auto text-emerald-600" size={32} />
        <div className="mt-2 text-sm text-slate-600">Your patient ID</div>
        <div className="text-2xl font-extrabold tracking-wide text-navy-900">{done}</div>
      </div>
      <Link to="/login" className="btn-primary mt-5 w-full !bg-navy-900 !py-2.5">Go to sign in</Link>
    </Frame>
  )
  return (
    <Frame title="Create patient account" subtitle="Enter your details. You can update height and weight later.">
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        <Field label="Full name" error={errors.full_name?.message}><input className="input" autoComplete="name" {...register('full_name', { required: 'Enter your name', minLength: { value: 2, message: 'Too short' } })} /></Field>
        <Field label="Email" error={errors.email?.message}><input type="email" className="input" autoComplete="email" {...register('email', { required: 'Enter your email' })} /></Field>
        <Field label="Password" error={errors.password?.message} hint="At least 8 characters with a letter and a digit">
          <PasswordInput autoComplete="new-password" error={errors.password} reg={register('password', { required: 'Choose a password', minLength: { value: 8, message: 'At least 8 characters' }, validate: (p) => (/[A-Za-z]/.test(p) && /\d/.test(p)) || 'Use a letter and a digit' })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Gender"><select className="input" {...register('sex')}><option value="">Select</option><option value="M">Male</option><option value="F">Female</option></select></Field>
          <Field label="Date of birth"><input type="date" className="input" max={new Date().toISOString().slice(0, 10)} {...register('date_of_birth')} /></Field>
        </div>
        <Field label="Phone (optional)"><input className="input" autoComplete="tel" {...register('phone')} /></Field>
        <div className="grid grid-cols-3 gap-3">
          <Field label="Height (cm)" error={errors.height_cm?.message}><input type="number" step="0.1" className="input" {...register('height_cm', { min: { value: 50, message: '50–250' }, max: { value: 250, message: '50–250' } })} /></Field>
          <Field label="Weight (kg)" error={errors.weight_kg?.message}><input type="number" step="0.1" className="input" {...register('weight_kg', { min: { value: 10, message: '10–400' }, max: { value: 400, message: '10–400' } })} /></Field>
          <Field label="BMI"><div className="input flex items-center bg-slate-50 font-semibold text-slate-700">{bmi ?? '—'}</div></Field>
        </div>
        {bmi && <p className="-mt-2 text-xs text-slate-500">{bmiBand(bmi)}</p>}
        {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</div>}
        <button className="btn-primary w-full !bg-navy-900 !py-2.5 hover:!bg-navy-800" disabled={isSubmitting}>{isSubmitting ? <Spinner size={16} /> : null}Create account</button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">Already registered? <Link to="/login" className="font-semibold text-brand-700 hover:underline">Sign in</Link></p>
    </Frame>
  )
}
