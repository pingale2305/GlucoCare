"""Authentication and AUTHORISATION dependencies. Every patient-scoped endpoint
goes through `patient_access`, so isolation is enforced on the server."""
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.database.session import get_db
from app.models import PatientAssignment, PatientProfile, User

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "User inactive or not found")
    return user


def doctor_user(user: User = Depends(current_user)) -> User:
    if user.role != "doctor" or not user.doctor_profile:
        raise HTTPException(403, "Doctor access required")
    return user


def is_assigned(db: Session, doctor_profile_id: int, patient_id: int) -> bool:
    return db.scalar(select(PatientAssignment.id).where(
        PatientAssignment.doctor_id == doctor_profile_id, PatientAssignment.patient_id == patient_id,
        PatientAssignment.active.is_(True))) is not None


class PatientCtx:
    def __init__(self, patient: PatientProfile, user: User):
        self.patient, self.user = patient, user

    @property
    def is_doctor(self) -> bool:
        return self.user.role == "doctor"


def patient_access(patient_id: int, request: Request, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> PatientCtx:
    """Patient -> only own record. Doctor -> only assigned patients."""
    patient = db.get(PatientProfile, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    if user.role == "patient":
        if patient.user_id != user.id:
            raise HTTPException(403, "You can only access your own records")
    elif user.role == "doctor":
        if not user.doctor_profile or not is_assigned(db, user.doctor_profile.id, patient.id):
            raise HTTPException(403, "This patient is not assigned to you")
    else:
        raise HTTPException(403, "Forbidden")
    return PatientCtx(patient, user)


def doctor_patient_access(ctx: PatientCtx = Depends(patient_access)) -> PatientCtx:
    if not ctx.is_doctor:
        raise HTTPException(403, "Doctor access required")
    return ctx


def patient_self_access(ctx: PatientCtx = Depends(patient_access)) -> PatientCtx:
    """Only the patient who owns the record (doctors can read but never write patient-entered data)."""
    if ctx.is_doctor:
        raise HTTPException(403, "Only the patient can add this entry")
    return ctx
