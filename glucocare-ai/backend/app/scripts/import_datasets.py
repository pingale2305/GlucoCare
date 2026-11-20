"""Import both supplied datasets into glucocare.db (safe to run repeatedly).

    python -m app.scripts.import_datasets
Requires the doctor account to exist (run app.scripts.seed first); imported patients are assigned to that doctor.
"""
import json
import sys

from sqlalchemy import select

from app.config import settings
from app.database.session import SessionLocal, init_db
from app.models import DoctorProfile, User
from app.services.importer import import_all


def main():
    settings.require_secret()
    init_db()
    db = SessionLocal()
    doc = db.scalar(select(User).where(User.email == settings.DOCTOR_EMAIL.lower(), User.role == "doctor"))
    if not doc:
        sys.exit("Doctor account not found. Run: python -m app.scripts.seed")
    print("Importing... (about 1-2 minutes the first time)")
    res = import_all(db, settings.EHC_FILE, settings.INBODY_FILE, doc.doctor_profile.id)
    print(json.dumps(res, indent=2))
    db.close()


if __name__ == "__main__":
    main()
