"""Unit tests for the pure (database-free) logic: alerts, organ risk screening, security, dataset cleaning."""
import os
from datetime import date, datetime

os.environ.setdefault("SECRET_KEY", "x" * 40)

import pandas as pd  # noqa: E402

from app.auth import security  # noqa: E402
from app.services import dataset_cleaning as dc, reference, risk  # noqa: E402
calc_bmi = reference.calc_bmi


def L(d, **kw):
    return {"collected_on": date.fromisoformat(d), **kw}


def test_password_hash_roundtrip():
    h = security.hash_password("Secret123")
    assert security.verify_password("Secret123", h)
    assert not security.verify_password("wrong", h)
    assert security.password_problem("short") and security.password_problem("onlyletters") is not None
    assert security.password_problem("Abcdefg1") is None


def test_jwt_roundtrip():
    p = security.decode_token(security.create_access_token(5, "doctor"))
    assert p["sub"] == "5" and p["role"] == "doctor"


def test_bmi_calculation():
    assert calc_bmi(170, 70) == 24.2
    assert calc_bmi(None, 70) is None


def test_alert_uses_latest_value_only():
    labs = [L("2024-01-01", hba1c=9.5, fbs=200), L("2025-01-01", hba1c=5.6, fbs=95)]
    assert reference.compute_alerts(labs, []) == []


def test_alert_hba1c_and_ppbs():
    a = reference.compute_alerts([L("2025-01-01", hba1c=9.4, ppbs=210)], [])
    keys = {x["rule_key"]: x["severity"] for x in a}
    assert keys["hba1c_marked_high"] == "high" and keys["ppbs_high"] == "moderate"


def test_critical_home_reading():
    now = datetime.now()
    a = reference.compute_alerts([], [{"measured_at": now, "value_mg_dl": 48, "context": "fasting"}], today=now.date())
    assert a and a[0]["severity"] == "critical"


def test_lab_flags_sex_specific():
    assert reference.lab_flag("hdl", 45, "F") == "L"
    assert reference.lab_flag("hdl", 45, "M") is None
    assert reference.lab_flag("ldl", 130, "M") == "H"


# ------------------------------------------------------------------ organ risk screening
def test_kidney_levels_with_markers():
    assert risk.assess([L("2025-01-01", egfr=95, urine_acr=10)], "M")["kidney"]["level"] == "low"
    assert risk.assess([L("2025-01-01", egfr=55)], "M")["kidney"]["level"] == "moderate"
    assert risk.assess([L("2025-01-01", egfr=80, urine_acr=450)], "F")["kidney"]["level"] == "high"
    assert risk.assess([L("2025-01-01", creatinine=1.5)], "M")["kidney"]["level"] == "moderate"
    assert risk.assess([L("2025-01-01", creatinine=2.4)], "M")["kidney"]["level"] == "high"


def test_appointment_slots():
    from app.services import appointments as ap
    d = date(2026, 11, 23)  # Monday
    starts = [s.strftime("%H:%M") for s in ap.slot_starts(d)]
    assert starts[0] == "10:00" and starts[1] == "10:40" and "13:20" not in starts and "14:00" in starts
    assert ap.slot_starts(date(2026, 11, 22)) == []  # Sunday
    now = datetime(2026, 11, 20, 9, 0)
    assert ap.is_valid_slot(datetime(2026, 11, 23, 10, 0), now) is None
    assert ap.is_valid_slot(datetime(2026, 11, 23, 10, 5), now)
    assert ap.is_valid_slot(datetime(2026, 11, 20, 9, 0), now)
    assert ap.is_valid_slot(datetime(2027, 3, 1, 10, 0), now)


def test_kidney_always_insufficient_without_kidney_markers():
    r = risk.assess([L("2025-01-01", uric_acid=9.5)], "M")
    assert r["kidney"]["level"] == "insufficient"
    assert "Insufficient data for kidney risk assessment" in r["kidney"]["message"]


def test_heart_levels():
    assert risk.assess([L("2025-01-01", total_cholesterol=170, ldl=80, hdl=55, triglycerides=110)], "M")["heart"]["level"] == "low"
    assert risk.assess([L("2025-01-01", total_cholesterol=210, ldl=120, hdl=55, triglycerides=110)], "M")["heart"]["level"] == "moderate"
    assert risk.assess([L("2025-01-01", total_cholesterol=260, ldl=170, hdl=35, triglycerides=220)], "M")["heart"]["level"] == "high"
    assert risk.assess([L("2025-01-01", ldl=120)], "M")["heart"]["level"] == "insufficient"
    assert risk.assess([], "M")["heart"]["level"] == "insufficient"


def test_low_hdl_alone_is_at_least_moderate():
    r = risk.assess([L("2025-01-01", total_cholesterol=150, ldl=70, hdl=13, triglycerides=100)], "M")["heart"]
    assert r["level"] == "moderate"


def test_liver_levels_and_source_date():
    assert risk.assess([L("2025-01-01", sgot=30, sgpt=28, ggtp=40)], "F")["liver"]["level"] == "low"
    mod = risk.assess([L("2025-01-01", sgot=30, sgpt=55)], "F")["liver"]
    assert mod["level"] == "moderate" and mod["source_date"] == "2025-01-01"
    assert risk.assess([L("2025-01-01", sgot=150, sgpt=130)], "F")["liver"]["level"] == "high"
    assert risk.assess([L("2025-01-01", ggtp=80)], "F")["liver"]["level"] == "insufficient"


def test_risk_has_dates_and_disclaimer():
    r = risk.assess([L("2025-03-04", sgot=30, sgpt=30)], "M", today=date(2026, 1, 1))
    assert r["prediction_date"] == "2026-01-01" and "not a medical diagnosis" in r["disclaimer"].lower()


def test_cleaning_ehc_and_linkage():
    raw = pd.DataFrame({"TRUNC(SPEC_COLLTD_DATE_TIME)": ["2024-01-01", "2024-01-01", "2025-01-01"], "PATIENT_ID": ["KH1000000001"] * 3,
                        "SEX": ["M"] * 3, "AGE": [50, 50, 51], "CONSULTANT_CODE": ["EHC"] * 3, "PRACTITIONER_NAME": ["EHC"] * 3,
                        "'FBS'": [100, 100, 5000], "'HBA1C'": [5.5, 5.5, 6.0]})
    df, rep = dc.clean_ehc(raw)
    assert len(df) == 2 and rep["duplicate_patient_date_rows_dropped"] == 1
    assert rep["implausible_values_set_to_null"] == {"fbs": 1}
    assert df["hospital_number"].iloc[0] == "1000000001"
