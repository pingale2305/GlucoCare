import { useState } from 'react'
import { useForm } from 'react-hook-form'
import api, { errMsg } from '../services/api'
import { todayISO } from '../utils/format'
import { Field, Spinner } from './ui'

export const GROUPS = [
  ['Kidney', [['creatinine', 'Creatinine', 'mg/dL'], ['egfr', 'eGFR', 'mL/min/1.73m²'], ['urine_acr', 'Urine albumin/creatinine', 'mg/g']]],
  ['Heart (lipids)', [['total_cholesterol', 'Total cholesterol', 'mg/dL'], ['ldl', 'LDL', 'mg/dL'], ['hdl', 'HDL', 'mg/dL'], ['triglycerides', 'Triglycerides', 'mg/dL']]],
  ['Liver', [['sgot', 'SGOT (AST)', 'U/L'], ['sgpt', 'SGPT (ALT)', 'U/L'], ['ggtp', 'GGTP', 'U/L']]],
  ['Diabetes', [['hba1c', 'HbA1c', '%'], ['fbs', 'Fasting glucose', 'mg/dL'], ['ppbs', 'Post-meal glucose', 'mg/dL']]],
]

/** Input grid for the report values; used by the doctor form and the patient upload form. */
export function LabFields({ register, cols = 'sm:grid-cols-3' }) {
  return GROUPS.map(([title, fields]) => (
    <div key={title}>
      <div className="mb-2 text-sm font-bold text-brand-800">{title}</div>
      <div className={`grid gap-3 ${cols}`}>
        {fields.map(([k, label, unit]) => (
          <Field key={k} label={`${label} (${unit})`}><input type="number" step="any" className="input" {...register(k)} /></Field>
        ))}
      </div>
    </div>
  ))
}

/** Doctor types in values from a patient's report. Only filled fields are saved. */
export default function LabEntryForm({ patientId, onSaved }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({ defaultValues: { collected_on: todayISO() } })
  const [error, setError] = useState('')
  const submit = async (v) => {
    setError('')
    const body = { collected_on: v.collected_on }
    GROUPS.forEach(([, fields]) => fields.forEach(([k]) => { if (v[k] !== '' && v[k] != null) body[k] = Number(v[k]) }))
    try { await api.post(`/api/doctor/patients/${patientId}/labs`, body); onSaved() } catch (e) { setError(errMsg(e)) }
  }
  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-5" noValidate>
      <Field label="Report date" error={errors.collected_on?.message}><input type="date" max={todayISO()} className="input sm:max-w-[200px]" {...register('collected_on', { required: 'Select the report date' })} /></Field>
      <LabFields register={register} />
      {error && <div role="alert" className="rounded-xl bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{error}</div>}
      <button className="btn-primary w-full" disabled={isSubmitting}>{isSubmitting && <Spinner size={16} />}Save values</button>
    </form>
  )
}
