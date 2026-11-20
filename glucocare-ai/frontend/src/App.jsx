import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { DoctorLayout, PatientLayout } from './layouts/Layouts'
import { Loading } from './components/ui'
import { Login, Register } from './pages/public/Auth'
import DoctorDashboard from './pages/doctor/DoctorDashboard'
import PatientsPage from './pages/doctor/PatientsPage'
import PatientReview from './pages/doctor/PatientReview'
import ReportsPage from './pages/doctor/ReportsPage'
import SuggestionsPage from './pages/doctor/SuggestionsPage'
import NotificationsPage from './pages/shared/NotificationsPage'
import AppointmentsPage from './pages/doctor/AppointmentsPage'
import PatientAppointments from './pages/patient/Appointments'
import { PatientDashboard, PatientFollowUps, PatientGlucose, PatientReports } from './pages/patient/Patient'

function Guard({ role, children }) {
  const { user, loading } = useAuth()
  if (loading) return <Loading />
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== role) return <Navigate to={`/${user.role}`} replace />
  return children
}

function Home() {
  const { user, loading } = useAuth()
  if (loading) return <Loading />
  return <Navigate to={user ? `/${user.role}` : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route path="/doctor" element={<Guard role="doctor"><DoctorLayout /></Guard>}>
        <Route index element={<DoctorDashboard />} />
        <Route path="patients" element={<PatientsPage />} />
        <Route path="review/:id" element={<PatientReview />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="suggestions" element={<SuggestionsPage />} />
        <Route path="appointments" element={<AppointmentsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
      </Route>

      <Route path="/patient" element={<Guard role="patient"><PatientLayout /></Guard>}>
        <Route index element={<PatientDashboard />} />
        <Route path="glucose" element={<PatientGlucose />} />
        <Route path="reports" element={<PatientReports />} />
        <Route path="follow-ups" element={<PatientFollowUps />} />
        <Route path="appointments" element={<PatientAppointments />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
