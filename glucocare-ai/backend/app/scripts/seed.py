"""Create the doctor account (credentials from .env). No demo or dummy patients are created.

    python -m app.scripts.seed
"""
import sys

from sqlalchemy import select

from app.auth.security import hash_password, password_problem
from app.config import settings
from app.database.session import SessionLocal, init_db
from app.models import DoctorProfile, User


def seed() -> None:
    settings.require_secret()
    if not settings.DOCTOR_EMAIL or not settings.DOCTOR_PASSWORD:
        sys.exit("Set DOCTOR_EMAIL and DOCTOR_PASSWORD in .env first.")
    if password_problem(settings.DOCTOR_PASSWORD):
        sys.exit("DOCTOR_PASSWORD: " + password_problem(settings.DOCTOR_PASSWORD))
    init_db()
    db = SessionLocal()
    doc = db.scalar(select(User).where(User.email == settings.DOCTOR_EMAIL.lower()))
    if not doc:
        doc = User(email=settings.DOCTOR_EMAIL.lower(), password_hash=hash_password(settings.DOCTOR_PASSWORD), role="doctor",
                   full_name=settings.DOCTOR_NAME)
        db.add(doc)
        db.flush()
        db.add(DoctorProfile(user_id=doc.id, specialization="Diabetology"))
        print("Doctor account created:", doc.email)
    else:
        print("Doctor account already exists:", doc.email)
    db.commit()
    db.close()


if __name__ == "__main__":
    seed()
