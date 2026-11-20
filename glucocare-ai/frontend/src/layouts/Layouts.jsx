import { Bell, CalendarDays, FileText, Footprints, LayoutDashboard, MessageSquareText, Users, Droplet } from 'lucide-react'
import Shell from './Shell'

const doctorNav = [
  { to: '/doctor', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/doctor/patients', label: 'Patient Review & Alerts', icon: Users },
  { to: '/doctor/reports', label: 'Report Management', icon: FileText },
  { to: '/doctor/suggestions', label: 'Doctor Suggestions', icon: MessageSquareText },
  { to: '/doctor/appointments', label: 'Appointments', icon: CalendarDays },
  { to: '/doctor/notifications', label: 'Notifications', icon: Bell },
]
const patientNav = [
  { to: '/patient', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/patient/glucose', label: 'My Glucose Readings', icon: Droplet },
  { to: '/patient/reports', label: 'My Reports', icon: FileText },
  { to: '/patient/follow-ups', label: 'Follow-ups', icon: Footprints },
  { to: '/patient/appointments', label: 'Appointments', icon: CalendarDays },
]

export const DoctorLayout = () => <Shell nav={doctorNav} title="Doctor portal" />
export const PatientLayout = () => <Shell nav={patientNav} title="Patient portal" />
