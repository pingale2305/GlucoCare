import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.auth.security import create_access_token, hash_password, password_problem, verify_password
from app.database.session import get_db
from app.models import BodyComposition, PatientProfile, User, utcnow
from app.schemas import LoginIn, RegisterIn
from app.services.records import audit, calc_bmi, new_patient_code, notify

router = APIRouter(prefix="/api/auth", tags=["auth"])

_FAILS: dict[str, list[float]] = {}
MAX_FAILS, WINDOW = 5, 15 * 60


def _locked(key: str) -> bool:
    now = time.time()
    _FAILS[key] = [t for t in _FAILS.get(key, []) if now - t < WINDOW]
    return len(_FAILS[key]) >= MAX_FAILS


def user_payload(u: User) -> dict:
    return {"id": u.id, "email": u.email, "role": u.role, "full_name": u.full_name,
            "patient_id": u.patient_profile.id if u.patient_profile else None,
            "patient_code": u.patient_profile.patient_code if u.patient_profile else None,
            "doctor_id": u.doctor_profile.id if u.doctor_profile else None}


@router.post("/register", status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    """Patient self-registration. Doctor accounts are created by the seed script. A new patient never
    receives imported history."""
    problem = password_problem(body.password)
    if problem:
        raise HTTPException(422, problem)
    if (body.height_cm is None) != (body.weight_kg is None):
        raise HTTPException(422, "Enter both height and weight, or leave both empty")
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password), role="patient", full_name=body.full_name.strip())
    db.add(user)
    db.flush()
    profile = PatientProfile(user_id=user.id, patient_code=new_patient_code(db), display_name=user.full_name, sex=body.sex,
                             date_of_birth=body.date_of_birth, phone=body.phone, source="self_registered")
    db.add(profile)
    db.flush()
    if body.height_cm and body.weight_kg:
        db.add(BodyComposition(patient_id=profile.id, test_datetime=utcnow().replace(microsecond=0), source="patient_entered",
                               height_cm=body.height_cm, weight_kg=body.weight_kg, bmi=calc_bmi(body.height_cm, body.weight_kg)))
    for d in db.scalars(select(User).where(User.role == "doctor", User.is_active.is_(True))):
        notify(db, d.id, "New patient registered", f"{user.full_name} ({profile.patient_code}) registered and is waiting to be assigned.",
               "/doctor/patients?tab=unassigned")
    audit(db, user, "register", "user", user.id, profile.id, ip=request.client.host if request.client else None)
    db.commit()
    return {"message": "Registration successful", "patient_code": profile.patient_code}


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.lower()
    if _locked(email):
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = db.scalar(select(User).where(User.email == email))
    ok = bool(user and user.is_active and verify_password(body.password, user.password_hash))
    if ok and body.role and user.role != body.role:
        ok = False
    if not ok:
        _FAILS.setdefault(email, []).append(time.time())
        audit(db, user, "login_failed", detail=email, ip=request.client.host if request.client else None)
        db.commit()
        raise HTTPException(401, "Incorrect email, password or role")
    _FAILS.pop(email, None)
    user.last_login = utcnow()
    audit(db, user, "login", "user", user.id, ip=request.client.host if request.client else None)
    db.commit()
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer", "user": user_payload(user)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_payload(user)
