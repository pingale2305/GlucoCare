"""Database-backed helpers shared by the API and the importer."""
from __future__ import annotations

import secrets
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (Alert, AuditLog, BodyComposition, DoctorProfile, GlucoseReading, LabResult, ManualLab, Notification,
                        PatientAssignment, PatientProfile, User, utcnow)
from app.services.dataset_cleaning import EHC_VALUE_COLUMNS
from app.services.reference import MANUAL_LAB_KEYS, calc_bmi, compute_alerts


def row_dict(obj, exclude: tuple = ()) -> dict:
    out = {}
    for c in obj.__table__.columns:
        if c.name in exclude:
            continue
        v = getattr(obj, c.name)
        out[c.name] = v.isoformat() if isinstance(v, (date, datetime)) else v
    return out


def audit(db: Session, user, action: str, entity: str | None = None, entity_id: int | None = None,
          patient_id: int | None = None, detail: str | None = None, ip: str | None = None) -> None:
    db.add(AuditLog(user_id=getattr(user, "id", None), action=action, entity=entity, entity_id=entity_id,
                    patient_id=patient_id, detail=(detail or "")[:500], ip=ip))


def notify(db: Session, user_id: int | None, title: str, message: str, link: str | None = None) -> None:
    if user_id:
        db.add(Notification(user_id=user_id, title=title[:200], message=message[:500], link=link))


def patient_label(p: PatientProfile) -> str:
    return p.display_name or p.external_id or p.patient_code


def notify_doctors(db: Session, patient: PatientProfile, title: str, message: str) -> None:
    """Notify the doctors assigned to the patient; if nobody is assigned yet, notify every doctor."""
    ids = [u for (u,) in db.execute(select(DoctorProfile.user_id).join(PatientAssignment, PatientAssignment.doctor_id == DoctorProfile.id)
                                    .where(PatientAssignment.patient_id == patient.id, PatientAssignment.active.is_(True)))]
    if ids:
        for uid in ids:
            notify(db, uid, title, message, f"/doctor/review/{patient.id}")
    else:  # not assigned yet: no patient details are shared with doctors who are not assigned
        for (uid,) in db.execute(select(User.id).where(User.role == "doctor", User.is_active.is_(True))):
            notify(db, uid, "Unassigned patient activity", "A registered patient who is waiting for assignment added new data.", "/doctor/patients?tab=unassigned")
    patient.updated_at = utcnow()


def new_patient_code(db: Session) -> str:
    while True:
        code = "GC-" + secrets.token_hex(3).upper()
        if not db.scalar(select(PatientProfile.id).where(PatientProfile.patient_code == code)):
            return code


def patient_age(p: PatientProfile) -> int | None:
    if p.date_of_birth:
        t = date.today()
        return t.year - p.date_of_birth.year - ((t.month, t.day) < (p.date_of_birth.month, p.date_of_birth.day))
    return p.age


def refresh_summary(db: Session, patient: PatientProfile) -> None:
    lab = db.scalar(select(LabResult).where(LabResult.patient_id == patient.id, LabResult.hba1c.is_not(None))
                    .order_by(LabResult.collected_on.desc()).limit(1))
    patient.latest_hba1c, patient.latest_hba1c_date = (lab.hba1c, lab.collected_on) if lab else (None, None)
    fbs = db.scalar(select(LabResult).where(LabResult.patient_id == patient.id, LabResult.fbs.is_not(None))
                    .order_by(LabResult.collected_on.desc()).limit(1))
    patient.latest_fbs = fbs.fbs if fbs else None
    patient.last_lab_date = db.scalar(select(LabResult.collected_on).where(LabResult.patient_id == patient.id)
                                      .order_by(LabResult.collected_on.desc()).limit(1))
    for m in db.scalars(select(ManualLab).where(ManualLab.patient_id == patient.id).order_by(ManualLab.collected_on)):
        if m.hba1c is not None and (patient.latest_hba1c_date is None or m.collected_on >= patient.latest_hba1c_date):
            patient.latest_hba1c, patient.latest_hba1c_date = m.hba1c, m.collected_on
        if m.fbs is not None:
            patient.latest_fbs = m.fbs
        if patient.last_lab_date is None or m.collected_on > patient.last_lab_date:
            patient.last_lab_date = m.collected_on
    ls = db.scalar(select(BodyComposition.test_datetime).where(BodyComposition.patient_id == patient.id)
                   .order_by(BodyComposition.test_datetime.desc()).limit(1))
    patient.last_scan_date = ls.date() if ls else None


def latest_body(db: Session, pid: int) -> dict:
    """Height / weight / BMI from the most recent body record (InBody import or patient entry)."""
    row = db.scalar(select(BodyComposition).where(BodyComposition.patient_id == pid, BodyComposition.weight_kg.is_not(None))
                    .order_by(BodyComposition.test_datetime.desc()).limit(1))
    if not row:
        h = db.scalar(select(BodyComposition.height_cm).where(BodyComposition.patient_id == pid, BodyComposition.height_cm.is_not(None))
                      .order_by(BodyComposition.test_datetime.desc()).limit(1))
        return {"height_cm": h, "weight_kg": None, "bmi": None, "measured_on": None, "source": None}
    h = row.height_cm
    if h is None:
        h = db.scalar(select(BodyComposition.height_cm).where(BodyComposition.patient_id == pid, BodyComposition.height_cm.is_not(None))
                      .order_by(BodyComposition.test_datetime.desc()).limit(1))
    bmi = row.bmi if row.bmi is not None else calc_bmi(h, row.weight_kg)
    return {"height_cm": h, "weight_kg": row.weight_kg, "bmi": bmi, "measured_on": row.test_datetime.date().isoformat(), "source": row.source}


def latest_glucose(db: Session, pid: int, lab_fallback: bool = False) -> dict | None:
    r = db.scalar(select(GlucoseReading).where(GlucoseReading.patient_id == pid).order_by(GlucoseReading.measured_at.desc()).limit(1))
    if r:
        return {"value": r.value_mg_dl, "at": r.measured_at.isoformat(), "context": r.context, "source": "patient_entered"}
    if lab_fallback:
        lab = db.scalar(select(LabResult).where(LabResult.patient_id == pid, LabResult.fbs.is_not(None)).order_by(LabResult.collected_on.desc()).limit(1))
        if lab:
            return {"value": lab.fbs, "at": lab.collected_on.isoformat(), "context": "fasting", "source": "lab"}
    return None


def latest_ppbs(db: Session, pid: int) -> float | None:
    rows = [r for r in lab_dicts(db, pid) if r.get("ppbs") is not None]
    return rows[-1]["ppbs"] if rows else None


def lab_dicts(db: Session, patient_id: int) -> list[dict]:
    """Imported EHC results plus values the doctor typed in from reports, oldest first."""
    rows = db.scalars(select(LabResult).where(LabResult.patient_id == patient_id)).all()
    out = [{"collected_on": r.collected_on, "source": r.source, **{c: getattr(r, c) for c in EHC_VALUE_COLUMNS}} for r in rows]
    for m, role in db.execute(select(ManualLab, User.role).outerjoin(User, User.id == ManualLab.entered_by).where(ManualLab.patient_id == patient_id)):
        out.append({"collected_on": m.collected_on, "source": "patient_entered" if role == "patient" else "doctor_entered",
                    **{c: getattr(m, c) for c in MANUAL_LAB_KEYS}})
    return sorted(out, key=lambda r: r["collected_on"])


def sync_alerts(db: Session, patient: PatientProfile) -> int:
    """Recompute rule-based alerts for one patient. Open alerts that no longer apply are removed;
    reviewed alerts are kept as history. Returns number of NEW alerts."""
    readings = [{"measured_at": r.measured_at, "value_mg_dl": r.value_mg_dl, "context": r.context} for r in db.scalars(
        select(GlucoseReading).where(GlucoseReading.patient_id == patient.id))]
    cands = compute_alerts(lab_dicts(db, patient.id), readings)
    keys = {(c["rule_key"], c["source_key"]) for c in cands}
    existing = {(a.rule_key, a.source_key): a for a in db.scalars(select(Alert).where(Alert.patient_id == patient.id))}
    new = 0
    for (rk, sk), a in existing.items():
        if a.status == "open" and (rk, sk) not in keys:
            db.delete(a)
    for c in cands:
        if (c["rule_key"], c["source_key"]) not in existing:
            db.add(Alert(patient_id=patient.id, **c))
            new += 1
    return new


def assign(db: Session, doctor_profile_id: int, patient_id: int) -> None:
    row = db.scalar(select(PatientAssignment).where(PatientAssignment.doctor_id == doctor_profile_id,
                                                    PatientAssignment.patient_id == patient_id))
    if row:
        row.active = True
    else:
        db.add(PatientAssignment(doctor_id=doctor_profile_id, patient_id=patient_id))


def save_manual_lab(db: Session, patient: PatientProfile, user, collected_on: date, data: dict) -> list[str]:
    """Store values typed from a report (one row per patient and date; later entries update the same row)."""
    values = {k: data[k] for k in MANUAL_LAB_KEYS if data.get(k) is not None}
    if not values:
        return []
    row = db.scalar(select(ManualLab).where(ManualLab.patient_id == patient.id, ManualLab.collected_on == collected_on))
    if row:
        for k, v in values.items():
            setattr(row, k, v)
    else:
        row = ManualLab(patient_id=patient.id, collected_on=collected_on, entered_by=user.id, **values)
        db.add(row)
    db.flush()
    refresh_summary(db, patient)
    sync_alerts(db, patient)
    audit(db, user, "save_report_values", "manual_lab", row.id, patient.id)
    return sorted(values)
