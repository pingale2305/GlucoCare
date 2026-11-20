"""Doctor endpoints. Every query is restricted to the logged-in doctor's ASSIGNED patients."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.auth.deps import PatientCtx, doctor_patient_access, doctor_user, is_assigned
from app.database.session import get_db
from app.models import (Alert, Appointment, BodyComposition, DoctorProfile, ManualLab, FoodEntry, GlucoseReading, LabResult, MedicalReport, PatientAssignment, PatientProfile,
                        StepEntry, Suggestion, User, utcnow)
from app.schemas import AcceptIn, AlertReviewIn, ManualLabIn, ProposeIn, SuggestionIn
from app.services import appointments as appt, risk
from app.services.dataset_cleaning import EHC_UNITS, EHC_VALUE_COLUMNS
from app.services.records import (assign, audit, save_manual_lab, lab_dicts, refresh_summary, sync_alerts, latest_body, latest_glucose, latest_ppbs, notify, patient_age, patient_label,
                                  row_dict)
from app.services.reference import (EXTRA_LAB_KEYS, MANUAL_LAB_KEYS, REVIEW_SEVERITIES, SEVERITY_ORDER, lab_flag,
                                    lab_parameters)

router = APIRouter(prefix="/api/doctor", tags=["doctor"])
SEV_RANK = case(*[(Alert.severity == k, v) for k, v in SEVERITY_ORDER.items()], else_=0)
LAB_KEYS = list(EHC_VALUE_COLUMNS) + list(EXTRA_LAB_KEYS)
INBODY_VIEW = ("test_datetime", "age_at_scan", "height_cm", "weight_kg", "bmi", "body_fat_percent", "skeletal_muscle_mass",
               "visceral_fat_level", "bmr", "inbody_score")


def _assigned_ids(doctor: User):
    return select(PatientAssignment.patient_id).where(PatientAssignment.doctor_id == doctor.doctor_profile.id, PatientAssignment.active.is_(True))


def _attention_ids(doctor: User):
    return select(Alert.patient_id).where(Alert.patient_id.in_(_assigned_ids(doctor)), Alert.status == "open",
                                          Alert.severity.in_(REVIEW_SEVERITIES))


def _list_item(db: Session, p: PatientProfile, attention: set) -> dict:
    body = latest_body(db, p.id)
    return {"id": p.id, "patient_code": p.patient_code, "external_id": p.external_id, "display_name": p.display_name,
            "age": patient_age(p), "sex": p.sex, "latest_hba1c": p.latest_hba1c, "latest_ppbs": latest_ppbs(db, p.id),
            "latest_glucose": latest_glucose(db, p.id, lab_fallback=True), "height_cm": body["height_cm"],
            "weight_kg": body["weight_kg"], "bmi": body["bmi"], "needs_attention": p.id in attention, "source": p.source}


# ---------------------------------------------------------------- dashboard
@router.get("/dashboard")
def dashboard(doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    ids = _assigned_ids(doctor)
    attention = set(db.scalars(_attention_ids(doctor)).all())
    alerts = db.execute(select(Alert, PatientProfile).join(PatientProfile, PatientProfile.id == Alert.patient_id).where(
        Alert.patient_id.in_(ids), Alert.status == "open", Alert.severity.in_(REVIEW_SEVERITIES))
        .order_by(SEV_RANK.desc(), Alert.measured_on.desc()).limit(8)).all()
    readings = db.execute(select(GlucoseReading, PatientProfile).join(PatientProfile, PatientProfile.id == GlucoseReading.patient_id).where(
        GlucoseReading.patient_id.in_(ids)).order_by(GlucoseReading.measured_at.desc()).limit(8)).all()
    recent = db.scalars(select(PatientProfile).where(PatientProfile.id.in_(ids)).order_by(PatientProfile.updated_at.desc(), PatientProfile.id).limit(6)).all()
    return {
        "total_patients": db.scalar(select(func.count()).select_from(PatientAssignment).where(
            PatientAssignment.doctor_id == doctor.doctor_profile.id, PatientAssignment.active.is_(True))) or 0,
        "requiring_attention": len(attention),
        "awaiting_assignment": _unassigned_count(db),
        "pending_appointments": db.scalar(select(func.count(Appointment.id)).where(
            Appointment.doctor_id == doctor.doctor_profile.id, Appointment.status == "pending", Appointment.start_at >= datetime.now())) or 0,
        "alerts": [{**row_dict(a, ("reviewed_by", "reviewed_at", "review_comment", "source_key", "threshold_kind")), "patient": patient_label(p)} for a, p in alerts],
        "recent_readings": [{**row_dict(r, ("notes", "entered_by")), "patient": patient_label(p), "patient_id": p.id} for r, p in readings],
        "recent_patients": [_list_item(db, p, attention) for p in recent]}


def _unassigned_q():
    return select(PatientProfile).where(PatientProfile.user_id.is_not(None), ~PatientProfile.id.in_(
        select(PatientAssignment.patient_id).where(PatientAssignment.active.is_(True))))


def _unassigned_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(_unassigned_q().subquery())) or 0


# ---------------------------------------------------------------- patient list / assignment
@router.get("/patients")
def patients(search: str = "", attention: bool = False, page: int = Query(1, ge=1), page_size: int = Query(20, ge=5, le=100),
             doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    q = select(PatientProfile).where(PatientProfile.id.in_(_assigned_ids(doctor)))
    if search.strip():
        s = f"%{search.strip()}%"
        q = q.where(or_(PatientProfile.display_name.ilike(s), PatientProfile.external_id.ilike(s),
                        PatientProfile.patient_code.ilike(s), PatientProfile.hospital_number.ilike(s)))
    att_all = set(db.scalars(_attention_ids(doctor)).all())
    if attention:
        q = q.where(PatientProfile.id.in_(_attention_ids(doctor)))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(PatientProfile.updated_at.desc(), PatientProfile.id).offset((page - 1) * page_size).limit(page_size)).all()
    return {"total": total, "page": page, "page_size": page_size, "items": [_list_item(db, p, att_all) for p in rows]}


@router.get("/patients/unassigned")
def unassigned(doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    rows = db.scalars(_unassigned_q().order_by(PatientProfile.created_at.desc())).all()
    return {"items": [{"id": p.id, "patient_code": p.patient_code, "display_name": p.display_name, "sex": p.sex,
                       "age": patient_age(p), "created_at": p.created_at.isoformat()} for p in rows]}


@router.post("/patients/{pid}/assign")
def assign_patient(pid: int, doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    p = db.get(PatientProfile, pid)
    if not p or p.user_id is None:
        raise HTTPException(404, "Patient not found")
    if db.scalar(select(PatientAssignment.id).where(PatientAssignment.patient_id == pid, PatientAssignment.active.is_(True))):
        raise HTTPException(409, "This patient is already assigned")
    assign(db, doctor.doctor_profile.id, pid)
    notify(db, p.user_id, "Doctor assigned", f"{doctor.full_name} is now your doctor.", "/patient")
    audit(db, doctor, "assign_patient", "patient", pid, pid)
    db.commit()
    return {"assigned": pid}


# ---------------------------------------------------------------- complete patient review
@router.get("/patients/{patient_id}/review")
def review(ctx: PatientCtx = Depends(doctor_patient_access), db: Session = Depends(get_db)):
    p = ctx.patient
    labs = lab_dicts(db, p.id)
    lab_rows = [{"collected_on": r["collected_on"].isoformat(), "source": r["source"],
                 "values": {k: r[k] for k in LAB_KEYS if r.get(k) is not None},
                 "flags": {k: f for k in LAB_KEYS if (f := lab_flag(k, r.get(k), p.sex))}} for r in reversed(labs)]
    scans = db.scalars(select(BodyComposition).where(BodyComposition.patient_id == p.id).order_by(BodyComposition.test_datetime.desc())).all()
    readings = db.scalars(select(GlucoseReading).where(GlucoseReading.patient_id == p.id).order_by(GlucoseReading.measured_at.desc()).limit(500)).all()
    food = db.scalars(select(FoodEntry).where(FoodEntry.patient_id == p.id).order_by(FoodEntry.entry_date.desc(), FoodEntry.id.desc()).limit(300)).all()
    steps = db.scalars(select(StepEntry).where(StepEntry.patient_id == p.id).order_by(StepEntry.entry_date.desc()).limit(365)).all()
    reports = db.scalars(select(MedicalReport).where(MedicalReport.patient_id == p.id).order_by(MedicalReport.created_at.desc())).all()
    sugg = db.execute(select(Suggestion, User.full_name).select_from(Suggestion).join(DoctorProfile, DoctorProfile.id == Suggestion.doctor_id)
                      .join(User, User.id == DoctorProfile.user_id).where(Suggestion.patient_id == p.id)
                      .order_by(Suggestion.suggestion_date.desc(), Suggestion.id.desc())).all()
    alerts = db.scalars(select(Alert).where(Alert.patient_id == p.id, Alert.status == "open", Alert.severity.in_(REVIEW_SEVERITIES))
                        .order_by(SEV_RANK.desc())).all()
    audit(db, ctx.user, "view_patient", "patient", p.id, p.id)
    db.commit()
    return {
        "profile": {"id": p.id, "patient_code": p.patient_code, "external_id": p.external_id, "hospital_number": p.hospital_number,
                    "display_name": p.display_name, "sex": p.sex, "age": patient_age(p),
                    "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None, "phone": p.phone, "source": p.source},
        "body": latest_body(db, p.id), "latest_hba1c": {"value": p.latest_hba1c, "date": p.latest_hba1c_date.isoformat() if p.latest_hba1c_date else None},
        "latest_ppbs": latest_ppbs(db, p.id), "latest_glucose": latest_glucose(db, p.id, lab_fallback=True),
        "labs": {"parameters": lab_parameters(), "units": EHC_UNITS, "items": lab_rows},
        "inbody": [{k: (getattr(s, k).isoformat() if k == "test_datetime" else getattr(s, k)) for k in INBODY_VIEW} | {"source": s.source} for s in scans],
        "readings": [row_dict(r, ("notes", "entered_by")) for r in readings],
        "food": [row_dict(f) for f in food], "steps": [row_dict(s) for s in steps],
        "reports": [row_dict(r, ("stored_name", "uploaded_by")) for r in reports],
        "suggestions": [{**row_dict(s), "doctor_name": n} for s, n in sugg],
        "risk": risk.assess(labs, p.sex),
        "alerts": [row_dict(a, ("source_key", "threshold_kind", "reviewed_by", "reviewed_at", "review_comment")) for a in alerts]}


# ---------------------------------------------------------------- alerts
@router.post("/alerts/{alert_id}/review")
def review_alert(alert_id: int, body: AlertReviewIn, doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    a = db.get(Alert, alert_id)
    if not a or not is_assigned(db, doctor.doctor_profile.id, a.patient_id):
        raise HTTPException(404, "Alert not found")
    a.status, a.reviewed_by, a.reviewed_at, a.review_comment = "reviewed", doctor.id, utcnow(), body.comment
    audit(db, doctor, "review_alert", "alert", a.id, a.patient_id)
    db.commit()
    return {"reviewed": a.id}


# ---------------------------------------------------------------- report management
@router.get("/reports")
def reports(doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    rows = db.execute(select(MedicalReport, PatientProfile).join(PatientProfile, PatientProfile.id == MedicalReport.patient_id).where(
        MedicalReport.patient_id.in_(_assigned_ids(doctor))).order_by(MedicalReport.created_at.desc()).limit(300)).all()
    return {"items": [{**row_dict(r, ("stored_name", "uploaded_by")), "patient_id": p.id, "patient_code": p.patient_code,
                       "patient_name": p.display_name} for r, p in rows]}


# ---------------------------------------------------------------- doctor suggestions
@router.get("/suggestions")
def list_suggestions(patient_id: int | None = None, doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    q = select(Suggestion, PatientProfile).join(PatientProfile, PatientProfile.id == Suggestion.patient_id).where(
        Suggestion.patient_id.in_(_assigned_ids(doctor)))
    if patient_id:
        q = q.where(Suggestion.patient_id == patient_id)
    rows = db.execute(q.order_by(Suggestion.suggestion_date.desc(), Suggestion.id.desc()).limit(300)).all()
    return {"items": [{**row_dict(s), "patient_code": p.patient_code, "patient_name": p.display_name, "external_id": p.external_id} for s, p in rows]}


@router.post("/patients/{pid}/suggestions", status_code=201)
def add_suggestion(pid: int, body: SuggestionIn, doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    p = db.get(PatientProfile, pid)
    if not p or not is_assigned(db, doctor.doctor_profile.id, pid):
        raise HTTPException(403, "This patient is not assigned to you")
    s = Suggestion(patient_id=pid, doctor_id=doctor.doctor_profile.id, content=body.content, suggestion_date=body.suggestion_date or date.today())
    db.add(s)
    db.flush()
    notify(db, p.user_id, "New suggestion from your doctor", body.content[:200], "/patient/follow-ups")
    audit(db, doctor, "add_suggestion", "suggestion", s.id, pid)
    db.commit()
    return row_dict(s)


@router.put("/suggestions/{sid}")
def edit_suggestion(sid: int, body: SuggestionIn, doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    s = db.get(Suggestion, sid)
    if not s or s.doctor_id != doctor.doctor_profile.id or not is_assigned(db, doctor.doctor_profile.id, s.patient_id):
        raise HTTPException(404, "Suggestion not found")
    s.content = body.content
    if body.suggestion_date:
        s.suggestion_date = body.suggestion_date
    p = db.get(PatientProfile, s.patient_id)
    notify(db, p.user_id, "Your doctor updated a suggestion", body.content[:200], "/patient/follow-ups")
    audit(db, doctor, "edit_suggestion", "suggestion", s.id, s.patient_id)
    db.commit()
    return row_dict(s)


# ---------------------------------------------------------------- lab values typed from a report
@router.post("/patients/{patient_id}/labs", status_code=201)
def add_lab_values(body: ManualLabIn, ctx: PatientCtx = Depends(doctor_patient_access), db: Session = Depends(get_db)):
    saved = save_manual_lab(db, ctx.patient, ctx.user, body.collected_on, body.model_dump())
    if not saved:
        raise HTTPException(422, "Enter at least one value")
    db.commit()
    return {"saved": saved}


# ---------------------------------------------------------------- appointments
def _appt_item(a: Appointment, p: PatientProfile) -> dict:
    return {**row_dict(a), "patient_code": p.patient_code, "patient_name": p.display_name}


def _doctor_appt(db: Session, doctor: User, aid: int) -> Appointment:
    a = db.get(Appointment, aid)
    if not a or a.doctor_id != doctor.doctor_profile.id:
        raise HTTPException(404, "Appointment not found")
    return a


def _slot_taken(db: Session, doctor_id: int, start: datetime, exclude: int | None = None) -> bool:
    q = select(Appointment.id).where(Appointment.doctor_id == doctor_id, Appointment.start_at == start, Appointment.status.in_(appt.ACTIVE))
    if exclude:
        q = q.where(Appointment.id != exclude)
    return db.scalar(q) is not None


@router.get("/appointments")
def appointments(doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Appointment, PatientProfile).join(PatientProfile, PatientProfile.id == Appointment.patient_id)
                      .where(Appointment.doctor_id == doctor.doctor_profile.id).order_by(Appointment.start_at.desc()).limit(300)).all()
    last = db.scalar(select(Appointment.zoom_url).where(Appointment.doctor_id == doctor.doctor_profile.id, Appointment.zoom_url.is_not(None))
                     .order_by(Appointment.updated_at.desc()).limit(1))
    return {"items": [_appt_item(a, p) for a, p in rows], "last_zoom_url": last, "minutes": 40}


@router.get("/appointments/slots")
def appointment_slots(day: date, doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    return {"slots": appt_slots(db, doctor.doctor_profile.id, day)}


def appt_slots(db: Session, doctor_id: int, day: date) -> list[dict]:
    now = datetime.now()
    taken = set(db.scalars(select(Appointment.start_at).where(
        Appointment.doctor_id == doctor_id, Appointment.status.in_(appt.ACTIVE),
        Appointment.start_at >= datetime.combine(day, datetime.min.time()),
        Appointment.start_at < datetime.combine(day, datetime.max.time()))).all())
    return [{"start": s.isoformat(timespec="minutes"), "available": s not in taken and appt.is_valid_slot(s, now) is None}
            for s in appt.slot_starts(day)]


@router.post("/appointments/{aid}/accept")
def accept_appointment(aid: int, body: AcceptIn, doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    a = _doctor_appt(db, doctor, aid)
    if a.status != "pending":
        raise HTTPException(409, "Only a pending request can be accepted")
    a.status, a.zoom_url = "accepted", body.zoom_url
    p = db.get(PatientProfile, a.patient_id)
    notify(db, p.user_id, "Appointment confirmed", f"{a.start_at:%a %d %b, %I:%M %p} · 40-minute Zoom call with {doctor.full_name}.", "/patient/appointments")
    audit(db, doctor, "accept_appointment", "appointment", a.id, a.patient_id)
    db.commit()
    return _appt_item(a, p)


@router.post("/appointments/{aid}/propose")
def propose_appointment(aid: int, body: ProposeIn, doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    a = _doctor_appt(db, doctor, aid)
    if a.status not in ("pending", "accepted"):
        raise HTTPException(409, "This appointment can no longer be changed")
    start = body.start_at.replace(tzinfo=None)
    problem = appt.is_valid_slot(start)
    if problem:
        raise HTTPException(422, problem)
    if _slot_taken(db, a.doctor_id, start, exclude=a.id):
        raise HTTPException(409, "That slot is already booked")
    if a.requested_start_at is None:
        a.requested_start_at = a.start_at
    a.start_at, a.status, a.zoom_url = start, "reschedule_proposed", body.zoom_url
    p = db.get(PatientProfile, a.patient_id)
    notify(db, p.user_id, "New appointment time proposed", f"{doctor.full_name} proposed {start:%a %d %b, %I:%M %p}. Please confirm.", "/patient/appointments")
    audit(db, doctor, "propose_appointment", "appointment", a.id, a.patient_id)
    db.commit()
    return _appt_item(a, p)


@router.post("/appointments/{aid}/cancel")
def cancel_appointment(aid: int, doctor: User = Depends(doctor_user), db: Session = Depends(get_db)):
    a = _doctor_appt(db, doctor, aid)
    if a.status not in appt.ACTIVE:
        raise HTTPException(409, "This appointment is already closed")
    a.status = "declined" if a.status == "pending" else "cancelled"
    p = db.get(PatientProfile, a.patient_id)
    notify(db, p.user_id, "Appointment cancelled", f"Your appointment on {a.start_at:%a %d %b, %I:%M %p} was cancelled by the doctor.", "/patient/appointments")
    audit(db, doctor, "cancel_appointment", "appointment", a.id, a.patient_id)
    db.commit()
    return _appt_item(a, p)
