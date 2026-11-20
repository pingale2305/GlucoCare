"""
Dataset inspection and cleaning for the two supplied source files.

* EHC data   : laboratory results (one row per patient per collection date)
* InBody 970 : body composition scans (one row per scan)

Nothing here modifies the original files. Cleaned working copies are returned
as DataFrames (and written to data/processed/ by `app.scripts.process_datasets`).
Every transformation is counted in the returned report so it can be documented.

No values are invented. The only "repairs" are:
  * whitespace / quote / bracket stripping on identifiers and column names
  * type coercion (text -> number / date)
  * values outside a wide physiological plausibility window are set to NULL
    (counted in the report, never replaced by an estimate)
  * exact duplicate (patient, date/time) rows are dropped (counted)
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# EHC (laboratory) data
# --------------------------------------------------------------------------- #
EHC_RENAME = {
    "TRUNC(SPEC_COLLTD_DATE_TIME)": "collected_on",
    "PATIENT_ID": "external_id",
    "SEX": "sex",
    "AGE": "age",
    "CONSULTANT_CODE": "consultant_code",
    "PRACTITIONER_NAME": "practitioner_name",
    "'ESR'": "esr",
    "'FBS'": "fbs",
    "'PPBS'": "ppbs",
    "'HBA1C'": "hba1c",
    "'INF'": "insulin_fasting",  # 'INF' is not documented in the file; see docs
    "'CHOL'": "total_cholesterol",
    "'HDLCHOL'": "hdl",
    "'TRIG'": "triglycerides",
    "'LDLCHOL'": "ldl",
    "'VLDL'": "vldl",
    "'SGOT'": "sgot",
    "'SGPT'": "sgpt",
    "'GGTP'": "ggtp",
    "'UA'": "uric_acid",
    "'VITB12'": "vitamin_b12",
    "'VITD1'": "vitamin_d",
    "'CA'": "calcium",
    "'TSH'": "tsh",
    "'CRP'": "crp",
}

# Units as best inferred from value ranges; confirm with the laboratory.
EHC_UNITS = {
    "esr": "mm/hr", "fbs": "mg/dL", "ppbs": "mg/dL", "hba1c": "%",
    "insulin_fasting": "(unconfirmed)", "total_cholesterol": "mg/dL", "hdl": "mg/dL",
    "triglycerides": "mg/dL", "ldl": "mg/dL", "vldl": "mg/dL", "sgot": "U/L",
    "sgpt": "U/L", "ggtp": "U/L", "uric_acid": "mg/dL", "vitamin_b12": "pg/mL",
    "vitamin_d": "ng/mL", "calcium": "mg/dL", "tsh": "uIU/mL", "crp": "mg/L",
}

# Wide windows: anything outside is physiologically implausible / unit error.
EHC_PLAUSIBLE = {
    "esr": (0, 150), "fbs": (20, 800), "ppbs": (20, 900), "hba1c": (3.0, 20.0),
    "insulin_fasting": (0, 1000), "total_cholesterol": (50, 700), "hdl": (5, 200),
    "triglycerides": (10, 5000), "ldl": (10, 600), "vldl": (1, 1000),
    "sgot": (1, 2000), "sgpt": (1, 2000), "ggtp": (1, 3000), "uric_acid": (0.5, 20),
    "vitamin_b12": (10, 10000), "vitamin_d": (0.1, 400), "calcium": (4, 16),
    "tsh": (0.001, 500), "crp": (0.01, 500),
}
EHC_VALUE_COLUMNS = list(EHC_UNITS.keys())


def read_ehc(path: str | Path) -> pd.DataFrame:
    """Read the EHC workbook. .xls needs `xlrd`; .xlsx needs `openpyxl`."""
    return pd.read_excel(path, sheet_name=0)


def clean_ehc(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report: dict = {"raw_rows": int(len(raw)), "raw_columns": [str(c) for c in raw.columns]}
    df = raw.rename(columns=lambda c: str(c).strip()).rename(columns=EHC_RENAME).copy()
    missing = [c for c in ("collected_on", "external_id", "sex", "age") if c not in df.columns]
    if missing:
        raise ValueError(f"EHC file is missing required columns: {missing}")

    df["external_id"] = df["external_id"].astype(str).str.strip().str.upper()
    df["hospital_number"] = df["external_id"].str.extract(r"(\d+)")[0]
    df["sex"] = df["sex"].astype(str).str.strip().str.upper().str[:1]
    df["collected_on"] = pd.to_datetime(df["collected_on"], errors="coerce")
    report["rows_with_bad_date"] = int(df["collected_on"].isna().sum())
    df = df.dropna(subset=["collected_on", "hospital_number"])
    df["collected_on"] = df["collected_on"].dt.date
    df["age"] = pd.to_numeric(df["age"], errors="coerce")

    for col in EHC_VALUE_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    nulled = {}
    for col, (lo, hi) in EHC_PLAUSIBLE.items():
        bad = df[col].notna() & ((df[col] < lo) | (df[col] > hi))
        if bad.any():
            nulled[col] = int(bad.sum())
            df.loc[bad, col] = np.nan
    report["implausible_values_set_to_null"] = nulled

    before = len(df)
    df = df.drop_duplicates(subset=["hospital_number", "collected_on"], keep="first")
    report["duplicate_patient_date_rows_dropped"] = int(before - len(df))

    keep = ["hospital_number", "external_id", "sex", "age", "collected_on",
            "consultant_code", "practitioner_name"] + EHC_VALUE_COLUMNS
    df = df[[c for c in keep if c in df.columns]].reset_index(drop=True)

    report.update({
        "clean_rows": int(len(df)),
        "unique_patients": int(df["hospital_number"].nunique()),
        "date_min": str(df["collected_on"].min()), "date_max": str(df["collected_on"].max()),
        "missing_by_column": {c: int(df[c].isna().sum()) for c in EHC_VALUE_COLUMNS},
    })
    vc = df["hospital_number"].value_counts()
    report["patients_with_2plus_visits"] = int((vc >= 2).sum())
    report["patients_with_3plus_visits"] = int((vc >= 3).sum())
    for k in ("hba1c", "fbs", "ppbs"):
        c = df.dropna(subset=[k])["hospital_number"].value_counts()
        report[f"patients_with_2plus_{k}"] = int((c >= 2).sum())
    return df, report


# --------------------------------------------------------------------------- #
# InBody 970 data
# --------------------------------------------------------------------------- #
# source column number -> clean field name (curated; the file has 262 columns,
# many of them empty or not used by the application)
INBODY_FIELDS = {
    2: "height_cm", 3: "gender", 4: "age", 5: "test_datetime", 6: "weight_kg",
    7: "weight_lower", 8: "weight_upper", 9: "tbw", 12: "icw", 15: "ecw",
    18: "protein", 21: "minerals", 24: "body_fat_mass", 25: "bfm_lower", 26: "bfm_upper",
    27: "soft_lean_mass", 30: "fat_free_mass", 33: "skeletal_muscle_mass",
    34: "smm_lower", 35: "smm_upper", 36: "bmi", 37: "bmi_lower", 38: "bmi_upper",
    39: "body_fat_percent", 40: "pbf_lower", 41: "pbf_upper",
    42: "lean_right_arm", 46: "lean_left_arm", 50: "lean_trunk", 54: "lean_right_leg",
    58: "lean_left_leg", 107: "ecw_tbw", 123: "inbody_score", 124: "target_weight",
    125: "weight_control", 126: "fat_control", 127: "muscle_control", 128: "bmr",
    129: "whr", 130: "whr_lower", 131: "whr_upper", 132: "visceral_fat_level",
    133: "visceral_fat_area", 137: "body_cell_mass", 142: "bone_mineral_content",
    146: "ffmi", 147: "fmi", 163: "phase_angle_50khz", 182: "smi",
    183: "recommended_calorie_intake", 184: "bmr_lower", 185: "bmr_upper",
}
INBODY_NUMERIC = [v for v in INBODY_FIELDS.values() if v not in ("gender", "test_datetime", "visceral_fat_level")] + ["visceral_fat_level"]
INBODY_PLAUSIBLE = {
    "height_cm": (80, 230), "weight_kg": (15, 300), "bmi": (8, 90),
    "body_fat_percent": (1, 80), "skeletal_muscle_mass": (3, 80), "bmr": (400, 4000),
    "visceral_fat_level": (1, 30), "visceral_fat_area": (0, 600),
}
# Columns the export fills with 0 / blank because the device option was not used.
INBODY_NOT_MEASURED = ["Systolic", "Diastolic", "Pulse", "Waist Circumference", "Visceral Fat (abdomen)", "Subcutaneous Fat"]


def read_inbody(path: str | Path) -> pd.DataFrame:
    """Reads every sheet. The first sheet has a header row; extra sheets in the
    supplied file have NO header row (same 262 columns, same order), so they are
    aligned by position to the first sheet's header."""
    sheets = pd.read_excel(path, sheet_name=None, header=None)
    names = list(sheets)
    main = sheets[names[0]]
    header = [str(h).strip() for h in main.iloc[0].tolist()]
    frames = [pd.DataFrame(main.iloc[1:].values, columns=header)]
    for n in names[1:]:
        extra = sheets[n]
        if extra.shape[1] != len(header):
            continue
        first = str(extra.iloc[0, 0])
        body = extra.iloc[1:] if first.strip().upper().startswith("SR") else extra
        frames.append(pd.DataFrame(body.values, columns=header))
    return pd.concat(frames, ignore_index=True)


def _col_by_number(df: pd.DataFrame, number: int) -> str | None:
    pat = re.compile(rf"^{number}\.\s")
    for c in df.columns:
        if pat.match(str(c)):
            return c
    return None


def clean_inbody(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report: dict = {"raw_rows": int(len(raw)), "raw_columns": int(raw.shape[1])}
    out = pd.DataFrame(index=raw.index)
    id_col = _col_by_number(raw, 1)
    if id_col is None:
        raise ValueError("InBody file: column '1. ID' not found")
    out["external_id"] = raw[id_col].astype(str).str.strip()
    out["hospital_number"] = out["external_id"].str.replace(r"\D", "", regex=True)
    for num, name in INBODY_FIELDS.items():
        col = _col_by_number(raw, num)
        out[name] = raw[col].values if col is not None else np.nan

    out["test_datetime"] = pd.to_datetime(out["test_datetime"], format="%d.%m.%Y %H:%M:%S", errors="coerce")
    report["rows_with_bad_date"] = int(out["test_datetime"].isna().sum())
    out["gender"] = out["gender"].astype(str).str.strip().str.upper().str[:1]
    out["visceral_fat_level"] = out["visceral_fat_level"].astype(str).str.extract(r"(\d+)")[0]
    for c in INBODY_NUMERIC:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out[out["test_datetime"].notna() & (out["hospital_number"].str.len() > 0)]
    nulled = {}
    for col, (lo, hi) in INBODY_PLAUSIBLE.items():
        bad = out[col].notna() & ((out[col] < lo) | (out[col] > hi))
        if bad.any():
            nulled[col] = int(bad.sum())
            out.loc[bad, col] = np.nan
    report["implausible_values_set_to_null"] = nulled

    before = len(out)
    out = out.drop_duplicates(subset=["hospital_number", "test_datetime"], keep="first")
    report["duplicate_patient_datetime_rows_dropped"] = int(before - len(out))
    out = out.reset_index(drop=True)

    vc = out["hospital_number"].value_counts()
    report.update({
        "clean_rows": int(len(out)),
        "unique_patients": int(out["hospital_number"].nunique()),
        "patients_with_2plus_scans": int((vc >= 2).sum()),
        "patients_with_3plus_scans": int((vc >= 3).sum()),
        "date_min": str(out["test_datetime"].min()), "date_max": str(out["test_datetime"].max()),
        "id_length_distribution": {str(k): int(v) for k, v in out["hospital_number"].str.len().value_counts().items()},
        "not_measured_in_export": INBODY_NOT_MEASURED,
    })
    return out, report


# --------------------------------------------------------------------------- #
# Linkage analysis
# --------------------------------------------------------------------------- #
def analyse_linkage(ehc: pd.DataFrame, inbody: pd.DataFrame) -> dict:
    """Both files carry the same hospital patient number (EHC 'KH1000001387',
    InBody '<1000001387>'). A link is accepted only when the numbers are equal
    AND the recorded sex agrees; disagreements are reported, never linked."""
    e = ehc.sort_values("collected_on").drop_duplicates("hospital_number")[["hospital_number", "sex", "age"]]
    i = inbody.sort_values("test_datetime").drop_duplicates("hospital_number")[["hospital_number", "gender", "age"]]
    j = e.merge(i, on="hospital_number", suffixes=("_ehc", "_inbody"))
    sex_ok = j["sex"] == j["gender"]
    return {
        "ehc_patients": int(e.shape[0]),
        "inbody_patients": int(i.shape[0]),
        "matching_hospital_numbers": int(j.shape[0]),
        "matching_with_same_sex": int(sex_ok.sum()),
        "matching_but_sex_differs_not_linked": int((~sex_ok).sum()),
        "median_abs_age_difference_years": float((j["age_ehc"] - j["age_inbody"]).abs().median()),
        "inbody_only_patients": int(len(set(i["hospital_number"]) - set(e["hospital_number"]))),
        "ehc_only_patients": int(len(set(e["hospital_number"]) - set(i["hospital_number"]))),
    }


def linked_numbers(ehc: pd.DataFrame, inbody: pd.DataFrame) -> set[str]:
    """Hospital numbers that may be linked (equal number and equal sex)."""
    e = ehc.drop_duplicates("hospital_number")[["hospital_number", "sex"]]
    i = inbody.drop_duplicates("hospital_number")[["hospital_number", "gender"]]
    j = e.merge(i, on="hospital_number")
    return set(j.loc[j["sex"] == j["gender"], "hospital_number"])
