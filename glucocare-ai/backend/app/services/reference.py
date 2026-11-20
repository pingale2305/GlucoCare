"""Reference ranges and transparent rule-based alerts.

These are plain threshold comparisons (not machine learning, not a diagnosis). Values are common adult
reference points; laboratories may use slightly different ranges.
"""
from __future__ import annotations

from datetime import date, timedelta

THRESHOLDS = {
    "hba1c_target": 7.0, "hba1c_marked_high": 9.0, "hba1c_low": 4.0,
    "fbs_low": 70.0, "fbs_high": 126.0, "ppbs_high": 180.0,
    "glucose_critical_low": 54.0, "glucose_critical_high": 300.0,
}
SEVERITY_ORDER = {"info": 0, "moderate": 1, "high": 2, "critical": 3}
REVIEW_SEVERITIES = ("moderate", "high", "critical")
# alert rules that existed in earlier versions of the app; removed from the database on start-up
REMOVED_RULES = ("hba1c_change", "hba1c_above_personal", "fbs_change", "ldl_high", "tg_high", "chol_high", "hdl_low",
                 "reading_outside_personal")


# ------------------------------------------------------------------ lab reference ranges (display flags)
# lo / hi are either a number or {"M": x, "F": y}. hi_excl: value must be BELOW hi (otherwise <= hi).
LAB_REFERENCE = {
    "hba1c": dict(label="HbA1c", group="Diabetes", hi=5.7, hi_excl=True, text="< 5.7"),
    "fbs": dict(label="Fasting glucose (FBS)", group="Diabetes", lo=70, hi=100, hi_excl=True, text="70 – 99"),
    "ppbs": dict(label="Post-meal glucose (PPBS)", group="Diabetes", hi=140, hi_excl=True, text="< 140"),
    "insulin_fasting": dict(label="Fasting insulin (INF)", group="Diabetes", text=""),
    "total_cholesterol": dict(label="Total cholesterol", group="Lipids", hi=200, hi_excl=True, text="< 200"),
    "ldl": dict(label="LDL cholesterol", group="Lipids", hi=100, hi_excl=True, text="< 100"),
    "hdl": dict(label="HDL cholesterol", group="Lipids", lo={"M": 40, "F": 50}, text="> 40 (M) / > 50 (F)"),
    "triglycerides": dict(label="Triglycerides", group="Lipids", hi=150, hi_excl=True, text="< 150"),
    "vldl": dict(label="VLDL", group="Lipids", hi=30, text="≤ 30"),
    "sgot": dict(label="SGOT (AST)", group="Liver", hi=40, text="≤ 40"),
    "sgpt": dict(label="SGPT (ALT)", group="Liver", hi=40, text="≤ 40"),
    "ggtp": dict(label="GGTP", group="Liver", hi=55, text="≤ 55"),
    "creatinine": dict(label="Creatinine", group="Kidney", hi={"M": 1.3, "F": 1.1}, text="≤ 1.3 (M) / ≤ 1.1 (F)"),
    "egfr": dict(label="eGFR", group="Kidney", lo=60, text="≥ 60"),
    "urine_acr": dict(label="Urine albumin/creatinine ratio", group="Kidney", hi=30, hi_excl=True, text="< 30"),
    "uric_acid": dict(label="Uric acid", group="Other", lo={"M": 3.4, "F": 2.4}, hi={"M": 7.0, "F": 6.0}, text="3.4–7.0 (M) / 2.4–6.0 (F)"),
    "tsh": dict(label="TSH", group="Other", lo=0.4, hi=4.0, text="0.4 – 4.0"),
    "vitamin_d": dict(label="Vitamin D", group="Other", lo=30, text="≥ 30"),
    "vitamin_b12": dict(label="Vitamin B12", group="Other", lo=200, hi=900, text="200 – 900"),
    "calcium": dict(label="Calcium", group="Other", lo=8.6, hi=10.2, text="8.6 – 10.2"),
    "esr": dict(label="ESR", group="Other", hi=20, text="≤ 20"),
    "crp": dict(label="CRP", group="Other", hi=5, hi_excl=True, text="< 5"),
}


def _pick(v, sex):
    if isinstance(v, dict):
        return v.get(sex) if sex in v else (min(v.values()) if True else None)
    return v


def lab_flag(key: str, value, sex: str | None):
    """'H' (above range), 'L' (below range) or None."""
    ref = LAB_REFERENCE.get(key)
    if not ref or value is None:
        return None
    lo, hi = ref.get("lo"), ref.get("hi")
    if isinstance(lo, dict):
        lo = lo.get(sex, min(lo.values()))
    if isinstance(hi, dict):
        hi = hi.get(sex, max(hi.values()))
    if lo is not None and value < lo:
        return "L"
    if hi is not None and (value >= hi if ref.get("hi_excl") else value > hi):
        return "H"
    return None


# values the doctor can type in from a report (stored separately from the imported EHC records)
EXTRA_LAB_KEYS = ("creatinine", "egfr", "urine_acr")
MANUAL_LAB_KEYS = ("hba1c", "fbs", "ppbs", "total_cholesterol", "ldl", "hdl", "triglycerides", "sgot", "sgpt", "ggtp",
                   "creatinine", "egfr", "urine_acr")
EXTRA_UNITS = {"creatinine": "mg/dL", "egfr": "mL/min/1.73m²", "urine_acr": "mg/g"}


def lab_parameters() -> list[dict]:
    from app.services.dataset_cleaning import EHC_UNITS
    out = []
    for key, r in LAB_REFERENCE.items():
        unit = EXTRA_UNITS.get(key) or EHC_UNITS.get(key, "")
        out.append({"key": key, "label": r["label"], "group": r["group"], "unit": "" if unit.startswith("(") else unit, "reference": r.get("text", "")})
    return out


def calc_bmi(height_cm, weight_kg):
    if not height_cm or not weight_kg:
        return None
    return round(weight_kg / ((height_cm / 100) ** 2), 1)


# ------------------------------------------------------------------ alerts
def _d(v) -> str:
    return v.isoformat()[:10] if hasattr(v, "isoformat") else str(v)[:10]


def compute_alerts(labs: list[dict], readings: list[dict], today: date | None = None) -> list[dict]:
    """labs: dicts with collected_on + analyte keys. readings: dicts with measured_at, value_mg_dl, context.
    Only the LATEST lab value of each analyte is judged, plus patient-entered readings from the last 30 days."""
    th = THRESHOLDS
    today = today or date.today()
    out: list[dict] = []

    def add(rule, meas, value, unit, when, sev, reason, ref):
        out.append({"rule_key": rule, "measurement": meas, "value": value, "unit": unit, "measured_on": _d(when),
                    "severity": sev, "reason": reason, "reference_text": ref, "threshold_kind": "reference",
                    "source_key": f"{_d(when)}|{value}"})

    labs = sorted(labs, key=lambda r: r["collected_on"])

    def latest(k):
        s = [(r["collected_on"], r[k]) for r in labs if r.get(k) is not None]
        return s[-1] if s else None

    s = latest("hba1c")
    if s:
        d, v = s
        if v >= th["hba1c_marked_high"]:
            add("hba1c_marked_high", "HbA1c", v, "%", d, "high", f"HbA1c {v}% on {_d(d)} is markedly above target.", f"Reference: marked elevation ≥ {th['hba1c_marked_high']}%")
        elif v > th["hba1c_target"]:
            add("hba1c_above_reference", "HbA1c", v, "%", d, "moderate", f"HbA1c {v}% on {_d(d)} is above the {th['hba1c_target']}% target.", f"Reference: target ≤ {th['hba1c_target']}%")
        if v < th["hba1c_low"]:
            add("hba1c_low", "HbA1c", v, "%", d, "moderate", f"HbA1c {v}% on {_d(d)} is unusually low.", f"Reference: ≥ {th['hba1c_low']}%")

    s = latest("fbs")
    if s:
        d, v = s
        if v < th["glucose_critical_low"]:
            add("fbs_critical_low", "Fasting glucose", v, "mg/dL", d, "critical", f"Fasting glucose {v} mg/dL on {_d(d)} is critically low.", f"Reference: ≥ {th['glucose_critical_low']} mg/dL")
        elif v < th["fbs_low"]:
            add("fbs_low", "Fasting glucose", v, "mg/dL", d, "high", f"Fasting glucose {v} mg/dL on {_d(d)} is below range.", f"Reference: ≥ {th['fbs_low']} mg/dL")
        elif v >= th["glucose_critical_high"]:
            add("fbs_critical_high", "Fasting glucose", v, "mg/dL", d, "critical", f"Fasting glucose {v} mg/dL on {_d(d)} is critically high.", f"Reference: < {th['glucose_critical_high']} mg/dL")
        elif v >= th["fbs_high"]:
            add("fbs_high", "Fasting glucose", v, "mg/dL", d, "moderate", f"Fasting glucose {v} mg/dL on {_d(d)} is at or above {th['fbs_high']} mg/dL.", f"Reference: < {th['fbs_high']} mg/dL")

    s = latest("ppbs")
    if s:
        d, v = s
        if v < th["glucose_critical_low"]:
            add("ppbs_critical_low", "Post-meal glucose", v, "mg/dL", d, "critical", f"Post-meal glucose {v} mg/dL on {_d(d)} is critically low.", f"Reference: ≥ {th['glucose_critical_low']} mg/dL")
        elif v >= th["glucose_critical_high"]:
            add("ppbs_critical_high", "Post-meal glucose", v, "mg/dL", d, "critical", f"Post-meal glucose {v} mg/dL on {_d(d)} is critically high.", f"Reference: < {th['glucose_critical_high']} mg/dL")
        elif v >= th["ppbs_high"]:
            add("ppbs_high", "Post-meal glucose", v, "mg/dL", d, "moderate", f"Post-meal glucose {v} mg/dL on {_d(d)} is at or above {th['ppbs_high']} mg/dL.", f"Reference: < {th['ppbs_high']} mg/dL")

    # patient-entered readings
    rd = sorted(readings, key=lambda r: r["measured_at"])
    for r in [x for x in rd if x["measured_at"].date() >= today - timedelta(days=30)]:
        v, t = r["value_mg_dl"], r["measured_at"]
        key = f"{t.isoformat(timespec='minutes')}|{v}"
        if v < th["glucose_critical_low"]:
            add("reading_critical_low", "Glucose reading", v, "mg/dL", t, "critical", f"Entered reading {v} mg/dL ({r.get('context')}) on {t:%Y-%m-%d %H:%M} is critically low.", f"Reference: ≥ {th['glucose_critical_low']} mg/dL")
            out[-1]["source_key"] = key
        elif v >= th["glucose_critical_high"]:
            add("reading_critical_high", "Glucose reading", v, "mg/dL", t, "critical", f"Entered reading {v} mg/dL ({r.get('context')}) on {t:%Y-%m-%d %H:%M} is critically high.", f"Reference: < {th['glucose_critical_high']} mg/dL")
            out[-1]["source_key"] = key
    if rd:
        r = rd[-1]
        v, t = r["value_mg_dl"], r["measured_at"]
        key = f"{t.isoformat(timespec='minutes')}|{v}"
        if not any(a["source_key"] == key for a in out):
            if v < th["fbs_low"]:
                add("reading_low", "Glucose reading", v, "mg/dL", t, "high", f"Latest entered reading {v} mg/dL ({r.get('context')}) on {t:%Y-%m-%d} is below {th['fbs_low']}.", f"Reference: ≥ {th['fbs_low']} mg/dL")
                out[-1]["source_key"] = key
            elif r.get("context") == "post_meal" and v >= th["ppbs_high"]:
                add("reading_high", "Glucose reading", v, "mg/dL", t, "moderate", f"Latest post-meal reading {v} mg/dL on {t:%Y-%m-%d} is at or above {th['ppbs_high']}.", f"Reference: < {th['ppbs_high']} mg/dL")
                out[-1]["source_key"] = key
    return out
