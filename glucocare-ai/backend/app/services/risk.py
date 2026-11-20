"""Organ-related risk SCREENING from recorded laboratory values.

This is transparent rule-based screening using common clinical reference points. It is NOT a trained machine
learning model: the supplied datasets contain no diagnosis or outcome labels, so a model could not be validated.
Each result lists the report values that produced it, the source report date and the date it was calculated.
It is decision-support information for the doctor and not a diagnosis.
"""
from __future__ import annotations

from datetime import date

LEVEL_LABEL = {"low": "Low Risk", "moderate": "Moderate Risk", "high": "High Risk", "insufficient": "Insufficient Data"}
METHOD = "Rule-based screening from recorded lab values"
DISCLAIMER = "Decision-support information for the doctor. Not a medical diagnosis."

HEART_KEYS = ("total_cholesterol", "ldl", "hdl", "triglycerides")
LIVER_KEYS = ("sgot", "sgpt", "ggtp")


def _row_with(labs: list[dict], keys) -> dict | None:
    """Most recent lab row that has at least one of the keys (values are taken from that single report)."""
    for r in sorted(labs, key=lambda r: r["collected_on"], reverse=True):
        if any(r.get(k) is not None for k in keys):
            return r
    return None


def _param(key, label, value, status, reference, unit="mg/dL"):
    return {"key": key, "label": label, "value": value, "unit": unit, "status": status, "reference": reference}


def heart(labs: list[dict], sex: str | None) -> dict:
    row = _row_with(labs, HEART_KEYS)
    out = {"level": "insufficient", "source_date": None, "parameters": [], "message": None}
    if not row:
        out["message"] = "Insufficient data for heart risk screening: no cholesterol, LDL, HDL or triglyceride values."
        return out
    params, n_high, score = [], 0, 0

    def tiered(key, label, b, h, ref):
        nonlocal n_high, score
        v = row.get(key)
        if v is None:
            return
        st = "high" if v >= h else "borderline" if v >= b else "normal"
        n_high += st == "high"
        score += {"high": 2, "borderline": 1, "normal": 0}[st]
        params.append(_param(key, label, v, st, ref))

    tiered("total_cholesterol", "Total cholesterol", 200, 240, "< 200")
    tiered("ldl", "LDL cholesterol", 100, 160, "< 100")
    tiered("triglycerides", "Triglycerides", 150, 200, "< 150")
    v = row.get("hdl")
    if v is not None:
        cut = 50 if sex == "F" else 40
        st = "low" if v < cut else "normal"
        score += st == "low"
        params.append(_param("hdl", "HDL cholesterol", v, st, f"> {cut}"))
    out["source_date"] = row["collected_on"].isoformat()[:10]
    out["parameters"] = params
    if len(params) < 2:
        out["message"] = "Insufficient data for heart risk screening: at least two lipid values are needed."
        return out
    ldl, tg = row.get("ldl"), row.get("triglycerides")
    if n_high >= 2 or (ldl is not None and ldl >= 190) or (tg is not None and tg >= 500):
        out["level"] = "high"
    elif n_high >= 1 or score >= 2 or any(q["key"] == "hdl" and q["status"] == "low" for q in params):
        out["level"] = "moderate"
    else:
        out["level"] = "low"
    return out


def liver(labs: list[dict]) -> dict:
    row = _row_with(labs, LIVER_KEYS)
    out = {"level": "insufficient", "source_date": None, "parameters": [], "message": None}
    if not row or (row.get("sgot") is None and row.get("sgpt") is None):
        out["message"] = "Insufficient data for liver risk screening: SGOT or SGPT is not available."
        return out
    uln = {"sgot": 40.0, "sgpt": 40.0, "ggtp": 55.0}
    label = {"sgot": "SGOT (AST)", "sgpt": "SGPT (ALT)", "ggtp": "GGTP"}
    params, ratios = [], []
    for k in LIVER_KEYS:
        v = row.get(k)
        if v is None:
            continue
        ratio = v / uln[k]
        ratios.append(ratio)
        st = "high" if ratio > 3 else "borderline" if ratio > 1 else "normal"
        params.append(_param(k, label[k], v, st, f"≤ {int(uln[k])}", "U/L"))
    out["parameters"] = params
    out["source_date"] = row["collected_on"].isoformat()[:10]
    if any(r > 3 for r in ratios) or sum(r > 2 for r in ratios) >= 2:
        out["level"] = "high"
    elif any(r > 1 for r in ratios):
        out["level"] = "moderate"
    else:
        out["level"] = "low"
    return out


def _latest(labs: list[dict], key: str):
    row = _row_with(labs, (key,))
    return (row[key], row["collected_on"]) if row else (None, None)


def kidney(labs: list[dict], sex: str | None = None) -> dict:
    """Needs eGFR, urine albumin (ACR) or creatinine. Uric acid alone is never used to assess the kidney."""
    out = {"level": "insufficient", "source_date": None, "parameters": [], "message": None}
    egfr, d1 = _latest(labs, "egfr")
    acr, d2 = _latest(labs, "urine_acr")
    cr, d3 = _latest(labs, "creatinine")
    params, levels, dates = [], [], []

    def add(key, label, v, unit, ref, status, level, d):
        params.append(_param(key, label, v, status, ref, unit))
        levels.append(level)
        dates.append(d)

    if egfr is not None:
        lv = "high" if egfr < 30 else "moderate" if egfr < 60 else "low"
        add("egfr", "eGFR", egfr, "mL/min/1.73m²", "≥ 60", {"high": "high", "moderate": "borderline", "low": "normal"}[lv], lv, d1)
    if acr is not None:
        lv = "high" if acr >= 300 else "moderate" if acr >= 30 else "low"
        add("urine_acr", "Urine albumin/creatinine", acr, "mg/g", "< 30", {"high": "high", "moderate": "borderline", "low": "normal"}[lv], lv, d2)
    if cr is not None:
        uln = 1.1 if sex == "F" else 1.3
        lv = "high" if cr >= 2.0 else "moderate" if cr > uln else "low"
        if egfr is None:  # creatinine is used on its own only when eGFR is missing
            add("creatinine", "Creatinine", cr, "mg/dL", f"≤ {uln}", {"high": "high", "moderate": "borderline", "low": "normal"}[lv], lv, d3)
        else:
            params.append(_param("creatinine", "Creatinine", cr, "info", f"≤ {uln}", "mg/dL"))
    ua, d4 = _latest(labs, "uric_acid")
    if not levels:
        out["message"] = "Insufficient data for kidney risk assessment: creatinine, eGFR and urine albumin are not in the reports."
        if ua is not None:
            out["parameters"] = [_param("uric_acid", "Uric acid (recorded, not sufficient alone)", ua, "info", "", "mg/dL")]
            out["source_date"] = d4.isoformat()[:10]
        return out
    out["parameters"] = params
    out["source_date"] = max(dates).isoformat()[:10]
    out["level"] = "high" if "high" in levels else "moderate" if "moderate" in levels else "low"
    return out


def assess(labs: list[dict], sex: str | None, today: date | None = None) -> dict:
    res = {"kidney": kidney(labs, sex), "heart": heart(labs, sex), "liver": liver(labs)}
    for v in res.values():
        v["label"] = LEVEL_LABEL[v["level"]]
    return {"method": METHOD, "disclaimer": DISCLAIMER, "prediction_date": (today or date.today()).isoformat(), **res}
