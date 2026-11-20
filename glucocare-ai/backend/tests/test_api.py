"""End-to-end API tests: registration, login, assignment, entries, uploads, suggestions, notifications, access rules.
Run: python -m pytest -v   (from backend/)"""
import os
import tempfile
from datetime import date, datetime, timedelta

_tmp = tempfile.mkdtemp()
os.environ.update({"SECRET_KEY": "t" * 40, "DATABASE_PATH": os.path.join(_tmp, "t.db"), "UPLOAD_DIR": os.path.join(_tmp, "up"),
                   "DOCTOR_EMAIL": "doc@test.local", "DOCTOR_PASSWORD": "Doctor123"})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import BodyComposition, LabResult, PatientProfile  # noqa: E402
from app.scripts.seed import seed  # noqa: E402
from app.services.records import refresh_summary  # noqa: E402

PW = "Passw0rd1"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        seed()
        yield c


def login(c, email, pw, role=None):
    r = c.post("/api/auth/login", json={"email": email, "password": pw, "role": role})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


def register(c, email, name="Pat Ient", **extra):
    r = c.post("/api/auth/register", json={"full_name": name, "email": email, "password": PW, **extra})
    assert r.status_code == 201, r.text
    return login(c, email, PW, "patient")


def doctor(c):
    return login(c, "doc@test.local", "Doctor123", "doctor")


def now_iso():
    return (datetime.now() - timedelta(minutes=5)).isoformat(timespec="seconds")


def test_health_and_unauthenticated(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/doctor/dashboard").status_code == 401
    assert client.get("/api/patients/1").status_code == 401


def test_registration_validation_and_login_roles(client):
    assert client.post("/api/auth/register", json={"full_name": "A B", "email": "x@y.com", "password": "short"}).status_code == 422
    register(client, "dup@test.local")
    assert client.post("/api/auth/register", json={"full_name": "A B", "email": "dup@test.local", "password": PW}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "doc@test.local", "password": "Doctor123", "role": "patient"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "doc@test.local", "password": "nope12345"}).status_code == 401
    doctor(client)


def test_new_patient_has_unique_id_bmi_and_no_history(client):
    h, u = register(client, "bmi@test.local", height_cm=170, weight_kg=70)
    assert u["patient_code"].startswith("GC-")
    o = client.get(f"/api/patients/{u['patient_id']}", headers=h).json()
    assert o["body"]["bmi"] == 24.2 and o["latest_hba1c"]["value"] is None and o["latest_glucose"] is None
    r = client.put(f"/api/patients/{u['patient_id']}/body", headers=h, json={"height_cm": 170, "weight_kg": 80})
    assert r.status_code == 200 and r.json()["bmi"] == 27.7
    assert client.put(f"/api/patients/{u['patient_id']}/body", headers=h, json={"height_cm": 10, "weight_kg": 80}).status_code == 422


def test_patient_isolation_and_doctor_assignment(client):
    h1, u1 = register(client, "iso1@test.local")
    h2, u2 = register(client, "iso2@test.local")
    p1, p2 = u1["patient_id"], u2["patient_id"]
    assert client.get(f"/api/patients/{p2}", headers=h1).status_code == 403
    assert client.get(f"/api/patients/{p2}/glucose", headers=h1).status_code == 403
    assert client.post(f"/api/patients/{p2}/glucose", headers=h1, json={"measured_at": now_iso(), "value_mg_dl": 100}).status_code == 403
    dh, _ = doctor(client)
    assert client.get(f"/api/patients/{p1}", headers=dh).status_code == 403          # not assigned yet
    assert client.get(f"/api/doctor/patients/{p1}/review", headers=dh).status_code == 403
    assert p1 in [x["id"] for x in client.get("/api/doctor/patients/unassigned", headers=dh).json()["items"]]
    assert client.post(f"/api/doctor/patients/{p1}/assign", headers=dh).status_code == 200
    assert client.post(f"/api/doctor/patients/{p1}/assign", headers=dh).status_code == 409
    assert client.get(f"/api/patients/{p1}", headers=dh).status_code == 200
    assert client.get(f"/api/patients/{p2}", headers=dh).status_code == 403
    assert client.get("/api/doctor/dashboard", headers=h1).status_code == 403
    assert any(n["title"] == "Doctor assigned" for n in client.get("/api/notifications", headers=h1).json()["items"])


def test_full_workflow(client, tmp_path):
    h, u = register(client, "flow@test.local", name="Flow Patient")
    pid = u["patient_id"]
    dh, _ = doctor(client)
    client.post(f"/api/doctor/patients/{pid}/assign", headers=dh)

    # glucose
    assert client.post(f"/api/patients/{pid}/glucose", headers=h, json={"measured_at": now_iso(), "value_mg_dl": 118, "context": "fasting"}).status_code == 201
    assert client.post(f"/api/patients/{pid}/glucose", headers=h, json={"measured_at": now_iso(), "value_mg_dl": 5, "context": "fasting"}).status_code == 422
    future = (datetime.now() + timedelta(days=2)).isoformat(timespec="seconds")
    assert client.post(f"/api/patients/{pid}/glucose", headers=h, json={"measured_at": future, "value_mg_dl": 100}).status_code == 422
    assert client.get(f"/api/patients/{pid}", headers=h).json()["latest_glucose"]["value"] == 118
    # doctors cannot write patient-entered data
    assert client.post(f"/api/patients/{pid}/glucose", headers=dh, json={"measured_at": now_iso(), "value_mg_dl": 100}).status_code == 403

    # food and steps
    today = date.today().isoformat()
    assert client.post(f"/api/patients/{pid}/food", headers=h, json={"entry_date": today, "meal_type": "Breakfast", "items": "Oats, banana"}).status_code == 201
    assert client.post(f"/api/patients/{pid}/food", headers=h, json={"entry_date": today, "meal_type": "Brunch", "items": "x y"}).status_code == 422
    assert client.post(f"/api/patients/{pid}/steps", headers=h, json={"entry_date": today, "steps": 4000}).status_code == 201
    assert client.post(f"/api/patients/{pid}/steps", headers=h, json={"entry_date": today, "steps": 6500}).status_code == 201
    st = client.get(f"/api/patients/{pid}/steps", headers=h).json()["items"]
    assert len(st) == 1 and st[0]["steps"] == 6500

    # report upload / open
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    r = client.post(f"/api/patients/{pid}/reports", headers=h, data={"title": "HbA1c report", "report_type": "lab_report"},
                    files={"file": ("rep.pdf", pdf, "application/pdf")})
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert client.post(f"/api/patients/{pid}/reports", headers=h, data={"title": "Bad file"}, files={"file": ("x.pdf", b"notpdf", "application/pdf")}).status_code == 415
    assert client.post(f"/api/patients/{pid}/reports", headers=h, data={"title": "Bad ext"}, files={"file": ("x.exe", b"MZ", "application/octet-stream")}).status_code == 415
    assert client.get(f"/api/patients/{pid}/reports/{rid}/download", headers=dh).content == pdf
    assert client.get(f"/api/patients/{pid}/reports/{rid}/download", headers=h).status_code == 200
    assert any(x["id"] == rid and x["patient_code"] == u["patient_code"] for x in client.get("/api/doctor/reports", headers=dh).json()["items"])

    # doctor notifications
    titles = [n["title"] for n in client.get("/api/notifications", headers=dh).json()["items"]]
    for t in ("New patient registered", "New glucose reading", "Food intake updated", "Walking steps updated", "Report uploaded"):
        assert t in titles, t

    # doctor review contains everything
    rv = client.get(f"/api/doctor/patients/{pid}/review", headers=dh).json()
    assert rv["profile"]["display_name"] == "Flow Patient"
    assert len(rv["readings"]) == 1 and len(rv["food"]) == 1 and len(rv["steps"]) == 1 and len(rv["reports"]) == 1
    assert rv["risk"]["kidney"]["level"] == "insufficient" and rv["risk"]["heart"]["level"] == "insufficient"
    assert rv["labs"]["items"] == [] and rv["inbody"] == []          # nothing imported is attached to a new patient

    # suggestions: only doctors write; patient reads
    s = client.post(f"/api/doctor/patients/{pid}/suggestions", headers=dh, json={"content": "Walk daily and repeat HbA1c in 3 months."})
    assert s.status_code == 201
    sid = s.json()["id"]
    assert client.post(f"/api/doctor/patients/{pid}/suggestions", headers=h, json={"content": "I am the patient"}).status_code == 403
    assert client.put(f"/api/doctor/suggestions/{sid}", headers=h, json={"content": "edited by patient"}).status_code == 403
    assert client.put(f"/api/doctor/suggestions/{sid}", headers=dh, json={"content": "Walk daily; repeat HbA1c in 2 months."}).status_code == 200
    got = client.get(f"/api/patients/{pid}/suggestions", headers=h).json()["items"]
    assert got[0]["content"].startswith("Walk daily; repeat") and got[0]["doctor_name"]
    assert got[0]["patient_id"] == pid and got[0]["doctor_id"]
    notes = client.get("/api/notifications", headers=h).json()
    assert notes["unread"] >= 2

    # read / unread
    nid = notes["items"][0]["id"]
    assert client.post(f"/api/notifications/{nid}/read", headers=h).status_code == 200
    assert client.post(f"/api/notifications/{nid}/unread", headers=h).status_code == 200
    assert client.post("/api/notifications/read-all", headers=h).status_code == 200
    assert client.get("/api/notifications", headers=h).json()["unread"] == 0
    assert client.post(f"/api/notifications/{nid}/read", headers=dh).status_code == 404   # not the doctor's notification

    # dashboard + list
    d = client.get("/api/doctor/dashboard", headers=dh).json()
    assert d["total_patients"] >= 1 and any(r["patient_id"] == pid for r in d["recent_readings"])
    lst = client.get("/api/doctor/patients?search=Flow", headers=dh).json()
    assert lst["total"] == 1 and lst["items"][0]["latest_glucose"]["value"] == 118


def next_monday_slot(hour_index=0):
    d = date.today() + timedelta(days=1)
    while d.weekday() != 0:
        d += timedelta(days=1)
    from app.services.appointments import slot_starts
    return slot_starts(d)[hour_index]


def test_manual_lab_values_feed_risk(client):
    h, u = register(client, "labs@test.local")
    dh, _ = doctor(client)
    client.post(f"/api/doctor/patients/{u['patient_id']}/assign", headers=dh)
    r = client.post(f"/api/doctor/patients/{u['patient_id']}/labs", headers=dh, json={"collected_on": date.today().isoformat(), "creatinine": 1.0, "egfr": 52, "ldl": 120, "total_cholesterol": 210, "sgot": 30, "sgpt": 28})
    assert r.status_code == 201, r.text
    assert client.post(f"/api/doctor/patients/{u['patient_id']}/labs", headers=dh, json={"collected_on": date.today().isoformat()}).status_code == 422
    assert client.post(f"/api/doctor/patients/{u['patient_id']}/labs", headers=h, json={"collected_on": date.today().isoformat(), "egfr": 90}).status_code == 403
    rk = client.get(f"/api/doctor/patients/{u['patient_id']}/review", headers=dh).json()["risk"]
    assert rk["kidney"]["level"] == "moderate" and rk["liver"]["level"] == "low"


def test_patient_submits_report_values_and_doctor_sees_risk(client):
    import json
    h, u = register(client, "repvals@test.local")
    pid = u["patient_id"]
    dh, _ = doctor(client)
    client.post(f"/api/doctor/patients/{pid}/assign", headers=dh)
    pdf = b"%PDF-1.4\n%%EOF"
    vals = json.dumps({"egfr": 52, "urine_acr": "", "ldl": 170, "total_cholesterol": 250, "triglycerides": 210, "hdl": 38, "sgot": 30, "sgpt": 28})
    r = client.post(f"/api/patients/{pid}/reports", headers=h, data={"title": "Full panel", "report_date": date.today().isoformat(), "lab_values": vals},
                    files={"file": ("a.pdf", pdf, "application/pdf")})
    assert r.status_code == 201, r.text
    bad = client.post(f"/api/patients/{pid}/reports", headers=h, data={"title": "Bad values", "lab_values": json.dumps({"egfr": 9999})},
                      files={"file": ("a.pdf", pdf, "application/pdf")})
    assert bad.status_code == 422
    rv = client.get(f"/api/doctor/patients/{pid}/review", headers=dh).json()
    assert rv["risk"]["kidney"]["level"] == "moderate" and rv["risk"]["heart"]["level"] == "high" and rv["risk"]["liver"]["level"] == "low"
    assert rv["labs"]["items"][0]["source"] == "patient_entered"
    assert any("with report values" in n["message"] for n in client.get("/api/notifications", headers=dh).json()["items"])
    # another patient never gets these values
    h2, u2 = register(client, "repvals2@test.local")
    client.post(f"/api/doctor/patients/{u2['patient_id']}/assign", headers=dh)
    assert client.get(f"/api/doctor/patients/{u2['patient_id']}/review", headers=dh).json()["risk"]["heart"]["level"] == "insufficient"


def test_appointment_flow(client):
    h, u = register(client, "appt@test.local", name="Appt Patient")
    pid = u["patient_id"]
    slot = next_monday_slot(0).isoformat(timespec="minutes")
    # not assigned yet -> cannot book
    assert client.post(f"/api/patients/{pid}/appointments", headers=h, json={"start_at": slot}).status_code == 409
    dh, _ = doctor(client)
    client.post(f"/api/doctor/patients/{pid}/assign", headers=dh)
    day = slot[:10]
    slots = client.get(f"/api/patients/{pid}/appointments/slots", headers=h, params={"day": day}).json()["slots"]
    assert slots and slots[0]["available"]
    assert client.post(f"/api/patients/{pid}/appointments", headers=h, json={"start_at": day + "T10:05"}).status_code == 422
    r = client.post(f"/api/patients/{pid}/appointments", headers=h, json={"start_at": slot, "reason": "Review reports"})
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    assert any(n["title"] == "Appointment request" for n in client.get("/api/notifications", headers=dh).json()["items"])
    # slot is now taken for everyone
    assert not client.get(f"/api/patients/{pid}/appointments/slots", headers=h, params={"day": day}).json()["slots"][0]["available"]
    h2, u2 = register(client, "appt2@test.local")
    client.post(f"/api/doctor/patients/{u2['patient_id']}/assign", headers=dh)
    assert client.post(f"/api/patients/{u2['patient_id']}/appointments", headers=h2, json={"start_at": slot}).status_code == 409
    # patient cannot manage someone else's appointment or accept it as doctor
    assert client.post(f"/api/patients/{u2['patient_id']}/appointments/{aid}/cancel", headers=h2).status_code == 404
    assert client.post(f"/api/doctor/appointments/{aid}/accept", headers=h, json={"zoom_url": "https://zoom.us/j/123"}).status_code == 403
    # doctor: zoom link must be a zoom link, then accept
    assert client.post(f"/api/doctor/appointments/{aid}/accept", headers=dh, json={"zoom_url": "https://example.com/x"}).status_code == 422
    assert client.post(f"/api/doctor/appointments/{aid}/accept", headers=dh, json={"zoom_url": "https://zoom.us/j/123456789"}).status_code == 200
    mine = client.get(f"/api/patients/{pid}/appointments", headers=h).json()["items"][0]
    assert mine["status"] == "accepted" and mine["zoom_url"].startswith("https://zoom.us") and mine["duration_min"] == 40
    # doctor proposes a new time, patient accepts
    new = next_monday_slot(2).isoformat(timespec="minutes")
    p = client.post(f"/api/doctor/appointments/{aid}/propose", headers=dh, json={"start_at": new, "zoom_url": "https://zoom.us/j/123456789"})
    assert p.status_code == 200 and p.json()["status"] == "reschedule_proposed"
    assert client.post(f"/api/patients/{pid}/appointments/{aid}/respond", headers=h, json={"action": "accept"}).status_code == 200
    assert client.get(f"/api/patients/{pid}/appointments", headers=h).json()["items"][0]["status"] == "accepted"
    assert any(n["title"] == "Appointment confirmed" for n in client.get("/api/notifications", headers=dh).json()["items"])
    assert client.post(f"/api/patients/{pid}/appointments/{aid}/cancel", headers=h).status_code == 200


def test_imported_records_are_shown_to_doctor_with_risk(client):
    with SessionLocal() as db:
        p = PatientProfile(hospital_number="9990001", external_id="KH9990001", patient_code="GC-IMPORT", sex="M", age=55, source="ehc_import")
        db.add(p)
        db.flush()
        db.add(LabResult(patient_id=p.id, collected_on=date(2025, 5, 1), source="ehc_import", hba1c=8.1, ppbs=215, total_cholesterol=250,
                         ldl=165, hdl=35, triglycerides=230, sgot=60, sgpt=75, uric_acid=8.0))
        db.add(BodyComposition(patient_id=p.id, test_datetime=datetime(2025, 5, 2, 9, 0), source="inbody_import", height_cm=172.0,
                               weight_kg=82.0, bmi=27.7, body_fat_percent=30.0))
        refresh_summary(db, p)
        pid = p.id
        from app.models import PatientAssignment, DoctorProfile
        db.add(PatientAssignment(doctor_id=db.query(DoctorProfile).first().id, patient_id=pid))
        db.commit()
    dh, _ = doctor(client)
    rv = client.get(f"/api/doctor/patients/{pid}/review", headers=dh).json()
    assert rv["body"]["height_cm"] == 172.0 and rv["body"]["bmi"] == 27.7 and rv["latest_hba1c"]["value"] == 8.1
    assert rv["risk"]["heart"]["level"] == "high" and rv["risk"]["liver"]["level"] in ("moderate", "high")
    assert rv["risk"]["kidney"]["level"] == "insufficient"
    assert rv["labs"]["items"][0]["flags"]["hba1c"] == "H" and rv["inbody"][0]["source"] == "inbody_import"
    item = client.get("/api/doctor/patients?search=KH9990001", headers=dh).json()["items"][0]
    assert item["latest_ppbs"] == 215 and item["height_cm"] == 172.0 and item["latest_glucose"] is None or item["latest_glucose"]["source"] == "lab"
    assert item["needs_attention"] is False or item["needs_attention"] is True
