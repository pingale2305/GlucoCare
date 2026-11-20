# API summary
Auth: `POST /api/auth/register`, `/login`, `GET /me`.
Patient (own record only; doctor read-only for assigned patients): `/api/patients/{id}` (+ `PUT /body`, `/glucose`, `/food`, `/steps`, `/suggestions`, `/reports`, `/reports/{rid}/download`).
Doctor: `/api/doctor/dashboard`, `/patients`, `/patients/unassigned`, `POST /patients/{id}/assign`, `/patients/{id}/review`, `/reports`, `/suggestions` (+ `POST /patients/{id}/suggestions`, `PUT /suggestions/{id}`), `POST /alerts/{id}/review`.
Notifications: `/api/notifications`, `POST /{id}/read`, `/{id}/unread`, `/read-all`.
Tables: users, doctor_profiles, patient_profiles, patient_assignments, lab_results (EHC), body_composition (InBody / patient-entered), glucose_readings, food_entries, step_entries, suggestions, medical_reports, alerts, notifications, dataset_import_logs, audit_logs.
