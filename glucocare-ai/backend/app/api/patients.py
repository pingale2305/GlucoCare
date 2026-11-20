"""Patient-scoped endpoints. Every route depends on `patient_access` (patient: own record only, doctor: assigned
patients only) or `patient_self_access` (only the owning patient may write)."""
import uuid
import json
from datetime import date, datetime
from pathlib import Path

from pydantic import ValidationError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import PatientCtx, patient_access, patient_self_access
from app.config import settings
from app.database.session import get_db
from app.models import (Appointment, BodyComposition, DoctorProfile, PatientAssignment, FoodEntry, GlucoseReading, MedicalReport, StepEntry, Suggestion, User,
                        utcnow)
from app.schemas import BodyIn, BookIn, ManualLabIn, FoodIn, GlucoseIn, RespondIn, StepsIn
from app.services import appointments as appt
from app.services.records import (save_manual_lab, audit, calc_bmi, latest_body, latest_glucose, notify, notify_doctors, patient_age, patient_label,
                                  row_dict, sync_alerts)

router = APIRouter(prefix="/api/patients/{patient_id}", tags=["patient records"])
MAGIC = {".pdf": (b"%PDF",), ".png": (b"\x89PNG",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",), ".xlsx": (b"PK\x03\x04",)}
REPORT_TYPES = ("lab_report", "prescription", "scan", "other")


def _ip(r: Request):
    return r.client.host if r.client else None


def profile_dict(p) -> dict:
    return {"id": p.id, "patient_code": p.patient_code, "display_name": p.display_name, "external_id": p.external_id,
            "sex": p.sex, "age": patient_age(p), "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
            "phone": p.phone, "source": p.source}


# ---------------------------------------------------------------- dashboard
@router.get("")
def overview(ctx: PatientCtx = Depends(patient_access), db: Session = Depends(get_db)):
    p = ctx.patient
    return {"profile": profile_dict(p), "latest_hba1c": {"value": p.latest_hba1c, "date": p.latest_hba1c_date.isoformat() if p.latest_hba1c_date else None},
            "latest_glucose": latest_glucose(db, p.id), "body": latest_body(db, p.id)}


@router.put("/body")
def update_body(body: BodyIn, request: Request, ctx: PatientCtx = Depends(patient_self_access), db: Session = Depends(get_db)):
    now = utcnow().replace(microsecond=0)
    bmi = calc_bmi(body.height_cm, body.weight_kg)
    row = db.scalar(select(BodyComposition).where(BodyComposition.patient_id == ctx.patient.id, BodyComposition.test_datetime == now))
    if row:
        row.height_cm, row.weight_kg, row.bmi = body.height_cm, body.weight_kg, bmi
    else:
        db.add(BodyComposition(patient_id=ctx.patient.id, test_datetime=now, source="patient_entered",
                               height_cm=body.height_cm, weight_kg=body.weight_kg, bmi=bmi))
    ctx.patient.updated_at = utcnow()
    audit(db, ctx.user, "update_body", "patient", ctx.patient.id, ctx.patient.id, ip=_ip(request))
    db.commit()
    return latest_body(db, ctx.patient.id)


# ---------------------------------------------------------------- glucose
@router.get("/glucose")
def glucose(ctx: PatientCtx = Depends(patient_access), db: Session = Depends(get_db)):
    rows = db.scalars(select(GlucoseReading).where(GlucoseReading.patient_id == ctx.patient.id)
                      .order_by(GlucoseReading.measured_at.desc()).limit(500)).all()
    return {"items": [row_dict(r, ("notes", "entered_by")) for r in rows]}


@router.post("/glucose", status_code=201)
def add_glucose(body: GlucoseIn, request: Request, ctx: PatientCtx = Depends(patient_self_access), db: Session = Depends(get_db)):
    p = ctx.patient
    r = GlucoseReading(patient_id=p.id, measured_at=body.measured_at, value_mg_dl=body.value_mg_dl, context=body.context,
                       source="patient_entered", entered_by=ctx.user.id)
    db.add(r)
    db.flush()
    sync_alerts(db, p)
    notify_doctors(db, p, "New glucose reading", f"{patient_label(p)} entered {body.value_mg_dl:g} mg/dL ({body.context.replace('_', '-')}).")
    audit(db, ctx.user, "add_glucose", "glucose_reading", r.id, p.id, ip=_ip(request))
    db.commit()
    return row_dict(r, ("notes", "entered_by"))


# ---------------------------------------------------------------- follow-ups: food + steps
@router.get("/food")
def food(ctx: PatientCtx = Depends(patient_access), db: Session = Depends(get_db)):
    rows = db.scalars(select(FoodEntry).where(FoodEntry.patient_id == ctx.patient.id)
                      .order_by(FoodEntry.entry_date.desc(), FoodEntry.id.desc()).limit(300)).all()
    return {"items": [row_dict(r) for r in rows]}


@router.post("/food", status_code=201)
def add_food(body: FoodIn, request: Request, ctx: PatientCtx = Depends(patient_self_access), db: Session = Depends(get_db)):
    p = ctx.patient
    f = FoodEntry(patient_id=p.id, entry_date=body.entry_date, meal_type=body.meal_type, items=body.items)
    db.add(f)
    db.flush()
    notify_doctors(db, p, "Food intake updated", f"{patient_label(p)} logged {body.meal_type.lower()} for {body.entry_date:%d %b %Y}.")
    audit(db, ctx.user, "add_food", "food_entry", f.id, p.id, ip=_ip(request))
    db.commit()
    return row_dict(f)


@router.get("/steps")
def steps(ctx: PatientCtx = Depends(patient_access), db: Session = Depends(get_db)):
    rows = db.scalars(select(StepEntry).where(StepEntry.patient_id == ctx.patient.id)
                      .order_by(StepEntry.entry_date.desc()).limit(365)).all()
    return {"items": [row_dict(r) for r in rows]}


@router.post("/steps", status_code=201)
def add_steps(body: StepsIn, request: Request, ctx: PatientCtx = Depends(patient_self_access), db: Session = Depends(get_db)):
    """One record per day: entering the same date again updates it."""
    p = ctx.patient
    s = db.scalar(select(StepEntry).where(StepEntry.patient_id == p.id, StepEntry.entry_date == body.entry_date))
    if s:
        s.steps = body.steps
    else:
        s = StepEntry(patient_id=p.id, entry_date=body.entry_date, steps=body.steps)
        db.add(s)
    db.flush()
    notify_doctors(db, p, "Walking steps updated", f"{patient_label(p)} recorded {body.steps:,} steps for {body.entry_date:%d %b %Y}.")
    audit(db, ctx.user, "save_steps", "step_entry", s.id, p.id, ip=_ip(request))
    db.commit()
    return row_dict(s)


# ---------------------------------------------------------------- doctor suggestions (read only here)
@router.get("/suggestions")
def suggestions(ctx: PatientCtx = Depends(patient_access), db: Session = Depends(get_db)):
    rows = db.execute(select(Suggestion, User.full_name).select_from(Suggestion).join(DoctorProfile, DoctorProfile.id == Suggestion.doctor_id)
                      .join(User, User.id == DoctorProfile.user_id).where(Suggestion.patient_id == ctx.patient.id)
                      .order_by(Suggestion.suggestion_date.desc(), Suggestion.id.desc()).limit(100)).all()
    return {"items": [{**row_dict(s), "doctor_name": name} for s, name in rows]}


# ---------------------------------------------------------------- reports
@router.get("/reports")
def list_reports(ctx: PatientCtx = Depends(patient_access), db: Session = Depends(get_db)):
    rows = db.scalars(select(MedicalReport).where(MedicalReport.patient_id == ctx.patient.id).order_by(MedicalReport.created_at.desc())).all()
    return {"items": [row_dict(r, ("stored_name", "uploaded_by")) for r in rows]}


@router.post("/reports", status_code=201)
async def upload_report(request: Request, title: str = Form(..., min_length=2, max_length=200), report_type: str = Form("lab_report"),
                        report_date: str | None = Form(None), lab_values: str | None = Form(None), file: UploadFile = File(...),
                        ctx: PatientCtx = Depends(patient_self_access), db: Session = Depends(get_db)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.ALLOWED_UPLOAD_EXT:
        raise HTTPException(415, f"File type not allowed. Use: {', '.join(sorted(settings.ALLOWED_UPLOAD_EXT))}")
    if report_type not in REPORT_TYPES:
        report_type = "other"
    rdate = None
    if report_date:
        try:
            rdate = datetime.strptime(report_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(422, "Invalid report date")
    lab_model = None
    if lab_values:
        try:
            raw = {k: v for k, v in json.loads(lab_values).items() if v not in (None, "")}
            if raw:
                lab_model = ManualLabIn(collected_on=rdate or date.today(), **raw)
        except (ValueError, TypeError, ValidationError) as e:
            msg = "; ".join(f"{(x['loc'] or ['value'])[-1]}: {x['msg']}" for x in e.errors()) if isinstance(e, ValidationError) else "Report values are not valid"
            raise HTTPException(422, msg)
    data = await file.read(settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {settings.MAX_UPLOAD_MB} MB")
    if not data:
        raise HTTPException(422, "The file is empty")
    if ext in MAGIC and not data.startswith(MAGIC[ext]):
        raise HTTPException(415, "File content does not match its extension")
    folder = Path(settings.UPLOAD_DIR) / str(ctx.patient.id)
    folder.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    (folder / stored).write_bytes(data)
    rep = MedicalReport(patient_id=ctx.patient.id, uploaded_by=ctx.user.id, title=title.strip(), report_type=report_type, report_date=rdate,
                        original_filename=Path(file.filename).name[:255], stored_name=stored,
                        content_type=file.content_type or "application/octet-stream", size_bytes=len(data))
    db.add(rep)
    db.flush()
    saved = save_manual_lab(db, ctx.patient, ctx.user, lab_model.collected_on, lab_model.model_dump()) if lab_model else []
    notify_doctors(db, ctx.patient, "Report uploaded", f"{patient_label(ctx.patient)} uploaded \"{rep.title}\"{' with report values' if saved else ''}.")
    audit(db, ctx.user, "upload_report", "medical_report", rep.id, ctx.patient.id, detail=rep.original_filename, ip=_ip(request))
    db.commit()
    return row_dict(rep, ("stored_name", "uploaded_by"))


@router.get("/reports/{rid}/download")
def download_report(rid: int, request: Request, ctx: PatientCtx = Depends(patient_access), db: Session = Depends(get_db)):
    r = db.get(MedicalReport, rid)
    if not r or r.patient_id != ctx.patient.id:
        raise HTTPException(404, "Report not found")
    path = Path(settings.UPLOAD_DIR) / str(ctx.patient.id) / r.stored_name
    if not path.is_file():
        raise HTTPException(404, "File is missing on the server")
    audit(db, ctx.user, "open_report", "medical_report", r.id, ctx.patient.id, ip=_ip(request))
    db.commit()
    return FileResponse(path, media_type=r.content_type, filename=r.original_filename)


# ---------------------------------------------------------------- appointments (40-minute Zoom call)
def _my_doctor(db: Session, patient_id: int):
    """(doctor profile id, doctor user id, doctor name) of the active assignment, or None."""
    row = db.execute(select(DoctorProfile.id, User.id, User.full_name).select_from(PatientAssignment)
                     .join(DoctorProfile, DoctorProfile.id == PatientAssignment.doctor_id).join(User, User.id == DoctorProfile.user_id)
                     .where(PatientAssignment.patient_id == patient_id, PatientAssignment.active.is_(True)).limit(1)).first()
    return row


def _appt_row(a: Appointment, doctor_name: str | None) -> dict:
    return {**row_dict(a), "doctor_name": doctor_name}


@router.get("/appointments")
def my_appointments(ctx: PatientCtx = Depends(patient_access), db: Session = Depends(get_db)):
    doc = _my_doctor(db, ctx.patient.id)
    rows = db.execute(select(Appointment, User.full_name).select_from(Appointment).join(DoctorProfile, DoctorProfile.id == Appointment.doctor_id)
                      .join(User, User.id == DoctorProfile.user_id).where(Appointment.patient_id == ctx.patient.id)
                      .order_by(Appointment.start_at.desc()).limit(100)).all()
    return {"has_doctor": doc is not None, "doctor_name": doc[2] if doc else None, "minutes": settings_minutes(),
            "items": [_appt_row(a, n) for a, n in rows]}


def settings_minutes() -> int:
    return settings.APPT_MINUTES


@router.get("/appointments/slots")
def free_slots(day: date, ctx: PatientCtx = Depends(patient_access), db: Session = Depends(get_db)):
    from app.api.doctor import appt_slots
    doc = _my_doctor(db, ctx.patient.id)
    return {"slots": appt_slots(db, doc[0], day) if doc else []}


@router.post("/appointments", status_code=201)
def book_appointment(body: BookIn, ctx: PatientCtx = Depends(patient_self_access), db: Session = Depends(get_db)):
    doc = _my_doctor(db, ctx.patient.id)
    if not doc:
        raise HTTPException(409, "You can book once your doctor has accepted your registration")
    start = body.start_at.replace(tzinfo=None)
    problem = appt.is_valid_slot(start)
    if problem:
        raise HTTPException(422, problem)
    if db.scalar(select(Appointment.id).where(Appointment.doctor_id == doc[0], Appointment.start_at == start, Appointment.status.in_(appt.ACTIVE))):
        raise HTTPException(409, "That slot was just booked. Please choose another time.")
    open_n = db.scalar(select(func.count(Appointment.id)).where(Appointment.patient_id == ctx.patient.id, Appointment.status.in_(appt.ACTIVE),
                                                                 Appointment.start_at >= datetime.now())) or 0
    if open_n >= 3:
        raise HTTPException(409, "You already have 3 upcoming appointments")
    a = Appointment(patient_id=ctx.patient.id, doctor_id=doc[0], start_at=start, duration_min=settings.APPT_MINUTES,
                    status="pending", reason=(body.reason or "").strip() or None)
    db.add(a)
    db.flush()
    notify(db, doc[1], "Appointment request", f"{patient_label(ctx.patient)} requested {start:%a %d %b, %I:%M %p}.", "/doctor/appointments")
    audit(db, ctx.user, "book_appointment", "appointment", a.id, ctx.patient.id)
    db.commit()
    return _appt_row(a, doc[2])


def _my_appt(db: Session, ctx: PatientCtx, aid: int) -> Appointment:
    a = db.get(Appointment, aid)
    if not a or a.patient_id != ctx.patient.id:
        raise HTTPException(404, "Appointment not found")
    return a


@router.post("/appointments/{aid}/respond")
def respond_to_proposal(aid: int, body: RespondIn, ctx: PatientCtx = Depends(patient_self_access), db: Session = Depends(get_db)):
    """Patient accepts or declines the new time proposed by the doctor."""
    a = _my_appt(db, ctx, aid)
    if a.status != "reschedule_proposed":
        raise HTTPException(409, "There is no proposed time to answer")
    doc = _my_doctor(db, ctx.patient.id)
    if body.action == "accept":
        if a.start_at < datetime.now():
            raise HTTPException(409, "That time has passed")
        a.status = "accepted"
    else:
        a.status = "cancelled"
    if doc:
        notify(db, doc[1], "Appointment " + ("confirmed" if body.action == "accept" else "declined"),
               f"{patient_label(ctx.patient)} {'accepted' if body.action == 'accept' else 'declined'} {a.start_at:%a %d %b, %I:%M %p}.", "/doctor/appointments")
    audit(db, ctx.user, "respond_appointment", "appointment", a.id, ctx.patient.id, detail=body.action)
    db.commit()
    return _appt_row(a, doc[2] if doc else None)


@router.post("/appointments/{aid}/cancel")
def cancel_my_appointment(aid: int, ctx: PatientCtx = Depends(patient_self_access), db: Session = Depends(get_db)):
    a = _my_appt(db, ctx, aid)
    if a.status not in appt.ACTIVE:
        raise HTTPException(409, "This appointment is already closed")
    a.status = "cancelled"
    doc = _my_doctor(db, ctx.patient.id)
    if doc:
        notify(db, doc[1], "Appointment cancelled", f"{patient_label(ctx.patient)} cancelled {a.start_at:%a %d %b, %I:%M %p}.", "/doctor/appointments")
    audit(db, ctx.user, "cancel_appointment", "appointment", a.id, ctx.patient.id)
    db.commit()
    return _appt_row(a, doc[2] if doc else None)
