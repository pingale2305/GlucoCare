"""Start-up clean-up of data left by earlier versions of the app (idempotent, safe to run every start)."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Alert, PatientProfile, User
from app.services.reference import REMOVED_RULES


def cleanup_legacy(db: Session) -> None:
    try:
        # synthetic demo patient from earlier versions
        for p in db.scalars(select(PatientProfile).where(PatientProfile.is_synthetic.is_(True))).all():
            uid = p.user_id
            db.delete(p)
            db.flush()
            if uid:
                u = db.get(User, uid)
                if u:
                    db.delete(u)
        # alert rules that no longer exist
        db.execute(delete(Alert).where(Alert.rule_key.in_(REMOVED_RULES)))
        db.execute(delete(Alert).where(Alert.threshold_kind != "reference"))
        db.commit()
    except Exception:
        db.rollback()
