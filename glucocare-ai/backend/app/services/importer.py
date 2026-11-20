"""Idempotent dataset import. Running it twice inserts nothing the second time.

* EHC rows        -> patient_profiles (keyed by hospital_number) + lab_results (source='ehc_import')
* InBody rows     -> body_composition, linked to a patient ONLY when the hospital number matches
                     AND the recorded sex agrees. Hospital numbers not present in the EHC file create a
                     separate InBody-only patient record. Number matches with conflicting sex are NOT
                     linked and are counted in the import log.
All imported patients are assigned to the given doctor so the doctor portal is usable.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BODY_FIELDS, BodyComposition, DatasetImportLog, LabResult, PatientAssignment, PatientProfile
from app.services import dataset_cleaning as dc
from app.services.records import new_patient_code, refresh_summary, sync_alerts


def _records(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")


def import_all(db: Session, ehc_path: str | Path, inbody_path: str | Path, doctor_profile_id: int | None = None,
               log=print) -> dict:
    ehc, ehc_rep = dc.clean_ehc(dc.read_ehc(ehc_path))
    inb, inb_rep = dc.clean_inbody(dc.read_inbody(inbody_path))
    summary = {}

    # ---------------- patients + labs
    existing = {p.hospital_number: p for p in db.scalars(select(PatientProfile).where(PatientProfile.hospital_number.is_not(None)))}
    created = 0
    latest = ehc.sort_values("collected_on").groupby("hospital_number").tail(1).set_index("hospital_number")
    for hn, row in latest.iterrows():
        if hn not in existing:
            p = PatientProfile(hospital_number=hn, external_id=row["external_id"], patient_code=new_patient_code(db),
                               sex=row["sex"], age=int(row["age"]) if pd.notna(row["age"]) else None, source="ehc_import")
            db.add(p); db.flush(); existing[hn] = p; created += 1
    log(f"EHC: {created} new patients")
    have_labs = {(pid, d) for pid, d in db.execute(select(LabResult.patient_id, LabResult.collected_on).where(LabResult.source == "ehc_import"))}
    new_labs, dup = [], 0
    for r in _records(ehc):
        pid = existing[r["hospital_number"]].id
        if (pid, r["collected_on"]) in have_labs:
            dup += 1; continue
        new_labs.append({"patient_id": pid, "collected_on": r["collected_on"], "source": "ehc_import",
                         **{c: r[c] for c in dc.EHC_VALUE_COLUMNS}})
    if new_labs:
        db.bulk_insert_mappings(LabResult, new_labs)
    db.add(DatasetImportLog(dataset="ehc", source_file=str(ehc_path), rows_read=ehc_rep["raw_rows"], rows_inserted=len(new_labs),
                            rows_skipped_duplicate=dup, patients_created=created, details=json.dumps(ehc_rep, default=str)))
    summary["ehc"] = {"rows_inserted": len(new_labs), "duplicates_skipped": dup, "patients_created": created}
    db.flush()

    # ---------------- InBody
    ehc_sex = {hn: s for hn, s in zip(ehc["hospital_number"], ehc["sex"])}
    inb_created, not_linked = 0, 0
    first_scan = inb.sort_values("test_datetime").groupby("hospital_number").head(1).set_index("hospital_number")
    for hn, row in first_scan.iterrows():
        if hn in existing:
            continue
        p = PatientProfile(hospital_number=hn, external_id=row["external_id"], patient_code=new_patient_code(db), sex=row["gender"],
                           age=int(row["age"]) if pd.notna(row["age"]) else None, source="inbody_import")
        db.add(p); db.flush(); existing[hn] = p; inb_created += 1
    have_scans = {(pid, dt) for pid, dt in db.execute(select(BodyComposition.patient_id, BodyComposition.test_datetime))}
    new_scans, dup2 = [], 0
    for r in _records(inb):
        hn = r["hospital_number"]
        if hn in ehc_sex and ehc_sex[hn] != r["gender"]:
            not_linked += 1; continue  # same number, conflicting sex -> do not link
        pid = existing[hn].id
        ts = r["test_datetime"].to_pydatetime() if hasattr(r["test_datetime"], "to_pydatetime") else r["test_datetime"]
        if (pid, ts) in have_scans:
            dup2 += 1; continue
        have_scans.add((pid, ts))
        new_scans.append({"patient_id": pid, "test_datetime": ts, "age_at_scan": int(r["age"]) if r["age"] is not None else None,
                          "source": "inbody_import", **{f: r.get(f) for f in BODY_FIELDS}})
    if new_scans:
        db.bulk_insert_mappings(BodyComposition, new_scans)
    db.add(DatasetImportLog(dataset="inbody", source_file=str(inbody_path), rows_read=inb_rep["raw_rows"], rows_inserted=len(new_scans),
                            rows_skipped_duplicate=dup2, rows_not_linked=not_linked, patients_created=inb_created,
                            details=json.dumps(inb_rep, default=str)))
    summary["inbody"] = {"rows_inserted": len(new_scans), "duplicates_skipped": dup2, "not_linked_sex_conflict": not_linked,
                         "inbody_only_patients_created": inb_created}
    db.flush()

    # ---------------- assignments, summaries, alerts
    assigned = {a.patient_id for a in db.scalars(select(PatientAssignment))}
    n_alerts = 0
    for p in existing.values():
        refresh_summary(db, p)
        if doctor_profile_id and p.id not in assigned:
            db.add(PatientAssignment(doctor_id=doctor_profile_id, patient_id=p.id))
        n_alerts += sync_alerts(db, p)
    db.commit()
    summary["alerts_created"] = n_alerts
    summary["total_patients"] = len(existing)
    return summary
