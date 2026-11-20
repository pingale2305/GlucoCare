# GlucoCare AI

Diabetes monitoring and decision-support for Dr. Dhaval. React + Vite + Tailwind frontend, FastAPI + SQLAlchemy backend, SQLite.

## Run (Windows, VS Code terminal, from this folder)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1      # first time only (venv, packages, dataset import)
powershell -ExecutionPolicy Bypass -File scripts\run-backend.ps1   # terminal 1  -> http://127.0.0.1:8000/docs
powershell -ExecutionPolicy Bypass -File scripts\run-frontend.ps1  # terminal 2  -> http://localhost:5173
powershell -ExecutionPolicy Bypass -File scripts\run-tests.ps1     # optional: backend tests
```

Doctor login: `doctor@glucocare.local` / `Doctor@12345` (set in `.env`). Patients register themselves on the Register page.

## Portals

- Patient: Dashboard, My Glucose Readings, My Reports, Follow-ups (food intake, walking steps, doctor suggestions), Appointments.
- Doctor: Dashboard, Patient Review & Alerts, Report Management, Doctor Suggestions, Appointments, Notifications.

## Data

`EHC_data_-_Dr_Dhaval.xls` and `inbody970_data_Excel_-_Dr_Dhaval.xlsx` (in `data/original/`) are imported once into `glucocare.db`; re-running the import adds nothing twice. Imported patients are assigned to the doctor. A newly registered patient starts empty and appears under *Patient Review & Alerts → Awaiting assignment* until the doctor assigns them.

Kidney / heart / liver cards are rule-based screening from report values (the datasets contain no outcome labels for a trained model). They are decision-support, not a diagnosis.

## Appointments
Patients pick a free 40-minute slot (Mon–Sat, 10:00–18:00, lunch 13:00–14:00; change in `.env` with `APPT_START_HOUR`, `APPT_END_HOUR`, `APPT_LUNCH_START`, `APPT_LUNCH_END`). The doctor is notified, then accepts (pasting his Zoom meeting link) or suggests a new date, which the patient confirms. Zoom links are the doctor's own meeting link; the app does not create Zoom meetings by itself.

## Lab values for new patients
Patients can type the values from their report while uploading it (*My Reports → Values from this report*); the doctor then sees the kidney / heart / liver cards straight away. Doctors can also type or correct values: on a patient's review page, *Lab reports → Enter values from a report* lets the doctor type creatinine, eGFR, urine ACR, lipids, liver enzymes and HbA1c from an uploaded report. These are stored separately as doctor-entered values and feed the kidney / heart / liver cards.
