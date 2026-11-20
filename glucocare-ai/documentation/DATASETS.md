# Datasets

Originals are never modified (`data/original/`). `python -m app.scripts.process_datasets` writes cleaned copies and `data/processed/dataset_quality_report.json`.

## EHC data (`EHC_data_-_Dr_Dhaval.xls`) — laboratory results
* 3,877 rows × 25 columns, **3,260 unique patients** (`KH` + 10 digits), collected 2024-01-02 → 2026-07-15. No duplicate (patient, date) rows.
* Columns: collection date, patient id, sex, age, consultant code (always "EHC"), practitioner (always "EHC"), ESR, FBS, PPBS, HbA1c, INF, total cholesterol, HDL, triglycerides, LDL, VLDL, SGOT, SGPT, GGTP, uric acid, vitamin B12, vitamin D, calcium, TSH, CRP.
* Missing values: HbA1c 480, PPBS 173, FBS 122, INF 774, CRP 3,679 (CRP is essentially unused), others 120–230.
* Repeated measurements: 522 patients have ≥2 visits, 89 have ≥3; **326 patients have ≥2 HbA1c**, 412 ≥2 FBS, 381 ≥2 PPBS. Visits are typically about a year apart.
* **No patient names, no medication, no diagnosis labels, no continuous glucose data.**
* "INF" meaning is not documented in the file (stored as `insulin_fasting`, flagged "unconfirmed"). Units are inferred from value ranges (glucose/lipids mg/dL, HbA1c %) — confirm with the laboratory.

## InBody 970 data (`inbody970_data_Excel_-_Dr_Dhaval.xlsx`) — body composition
* Sheet 1: 3,906 scans × 262 columns with header. Sheet "Sheet1": 7 extra scans, **no header row**, same 262 columns — aligned by position.
* 3,913 scans, **3,431 patients**, 2024-01-02 → 2026-07-16. 335 patients have ≥2 scans, 68 have ≥3.
* Used (curated ~50 columns): height, weight, BMI, body fat mass/%, skeletal muscle mass, soft lean mass, fat-free mass, water, protein, minerals, visceral fat level (text "level 9" parsed to 9) and area, BMR, WHR, InBody score, target weight, segmental lean mass, device reference limits.
* Not measured in the export (all zero/blank): blood pressure, waist circumference, subcutaneous fat, growth score and similar — never displayed.
* Patient IDs are `<1000084466>`; 25 IDs have 9 or 11 digits (data-quality note), 7 rows (Sheet1) use a different ID scheme.

## Linkage
* All 3,260 EHC patients also exist in the InBody file (same hospital number); 171 InBody-only patients exist.
* Rule: link only if hospital number equal **and** sex equal → 3,256 linked, **4 conflicts not linked** (logged). Median age difference between the files is 1 year (scan vs sample date).

## Cleaning steps (all counted in the quality report)
1. Strip quotes/brackets/whitespace from column names and IDs; parse dates (`dd.mm.yyyy hh:mm:ss` for InBody).
2. Coerce numerics; values outside wide physiological windows set to NULL (1 total-cholesterol value of 4.92 mg/dL in the real data). Never imputed.
3. Drop exact duplicate (patient, date/time) rows (0 found).
4. Database import is idempotent (unique constraints + existence checks): re-running inserts nothing.
5. Imported rows are tagged `source='ehc_import'` / `'inbody_import'`; patient-entered readings live in a separate table.
