from datetime import date, datetime, timezone

from sqlalchemy import (Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.services.dataset_cleaning import EHC_VALUE_COLUMNS, INBODY_FIELDS
from app.services.reference import MANUAL_LAB_KEYS


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)  # doctor | patient
    full_name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False)
    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False)


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    specialization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    license_no: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user = relationship("User", back_populates="doctor_profile")


class PatientProfile(Base):
    """One row per patient. Imported EHC/InBody patients have no login (user_id is NULL).
    No diagnosis, diabetes type, conditions or medication fields exist - only what the datasets contain
    plus what the patient/doctor enter in the application."""
    __tablename__ = "patient_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    hospital_number: Mapped[str | None] = mapped_column(String(30), unique=True, index=True, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)  # e.g. KH1000001387
    patient_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)          # e.g. GC-6BE6BC
    display_name: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(1), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)  # age recorded in the source file
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="self_registered")  # ehc_import | inbody_import | self_registered
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    # summary of the latest imported values, refreshed by services.records.refresh_summary
    latest_hba1c: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    latest_hba1c_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    latest_fbs: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_lab_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    last_scan_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, index=True)
    user = relationship("User", back_populates="patient_profile")


class PatientAssignment(Base):
    __tablename__ = "patient_assignments"
    __table_args__ = (UniqueConstraint("doctor_id", "patient_id", name="uq_assignment"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LabResult(Base):
    """Laboratory results (EHC dataset). source='ehc_import' for imported rows."""
    __tablename__ = "lab_results"
    __table_args__ = (UniqueConstraint("patient_id", "collected_on", "source", name="uq_lab_patient_date_source"),
                      Index("ix_lab_patient_date", "patient_id", "collected_on"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"))
    collected_on: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(20), default="ehc_import")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    for _c in EHC_VALUE_COLUMNS:
        locals()[_c] = mapped_column(Float, nullable=True)
    del _c


BODY_FIELDS = [v for v in INBODY_FIELDS.values() if v not in ("gender", "test_datetime", "age")]


class BodyComposition(Base):
    """InBody scans (source='inbody_import') and patient-entered height/weight/BMI (source='patient_entered')."""
    __tablename__ = "body_composition"
    __table_args__ = (UniqueConstraint("patient_id", "test_datetime", name="uq_body_patient_dt"),
                      Index("ix_body_patient_dt", "patient_id", "test_datetime"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"))
    test_datetime: Mapped[datetime] = mapped_column(DateTime)
    age_at_scan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="inbody_import")
    for _c in BODY_FIELDS:
        locals()[_c] = mapped_column(Float, nullable=True)
    del _c


class GlucoseReading(Base):
    """Readings entered by the patient. Never mixed with imported lab data."""
    __tablename__ = "glucose_readings"
    __table_args__ = (Index("ix_glucose_patient_time", "patient_id", "measured_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"))
    measured_at: Mapped[datetime] = mapped_column(DateTime)
    value_mg_dl: Mapped[float] = mapped_column(Float)
    context: Mapped[str] = mapped_column(String(20), default="random")  # fasting|post_meal|random|bedtime
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="patient_entered")
    entered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FoodEntry(Base):
    __tablename__ = "food_entries"
    __table_args__ = (Index("ix_food_patient_date", "patient_id", "entry_date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"))
    entry_date: Mapped[date] = mapped_column(Date)
    meal_type: Mapped[str] = mapped_column(String(20))  # Breakfast | Lunch | Snacks | Dinner
    items: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class StepEntry(Base):
    __tablename__ = "step_entries"
    __table_args__ = (UniqueConstraint("patient_id", "entry_date", name="uq_steps_patient_date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True)
    entry_date: Mapped[date] = mapped_column(Date)
    steps: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Suggestion(Base):
    """The doctor's written suggestion for a patient. Only doctors can create/edit."""
    __tablename__ = "suggestions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    suggestion_date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class MedicalReport(Base):
    __tablename__ = "medical_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    report_type: Mapped[str] = mapped_column(String(40), default="lab_report")
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("patient_id", "rule_key", "source_key", name="uq_alert"),
                      Index("ix_alert_status_sev", "status", "severity"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True)
    rule_key: Mapped[str] = mapped_column(String(50))
    source_key: Mapped[str] = mapped_column(String(80))
    measurement: Mapped[str] = mapped_column(String(50))
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    measured_on: Mapped[str | None] = mapped_column(String(30), nullable=True)
    severity: Mapped[str] = mapped_column(String(10))  # info | moderate | high | critical
    threshold_kind: Mapped[str] = mapped_column(String(12), default="reference")
    reason: Mapped[str] = mapped_column(String(500))
    reference_text: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)  # open | reviewed
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(500))
    link: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class DatasetImportLog(Base):
    __tablename__ = "dataset_import_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset: Mapped[str] = mapped_column(String(30))
    source_file: Mapped[str] = mapped_column(String(300))
    rows_read: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped_duplicate: Mapped[int] = mapped_column(Integer, default=0)
    rows_not_linked: Mapped[int] = mapped_column(Integer, default=0)
    patients_created: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    patient_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ManualLab(Base):
    """Lab values typed in by the doctor from a patient's report (separate from the imported EHC records)."""
    __tablename__ = "manual_labs"
    __table_args__ = (UniqueConstraint("patient_id", "collected_on", name="uq_manual_lab_patient_date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True)
    collected_on: Mapped[date] = mapped_column(Date)
    entered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    for _c in MANUAL_LAB_KEYS:
        locals()[_c] = mapped_column(Float, nullable=True)
    del _c


class Appointment(Base):
    """40-minute Zoom appointment. status: pending | accepted | reschedule_proposed | declined | cancelled."""
    __tablename__ = "appointments"
    __table_args__ = (Index("ix_appt_doctor_start", "doctor_id", "start_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime)
    duration_min: Mapped[int] = mapped_column(Integer, default=40)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    zoom_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    requested_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
