"""Create cleaned working copies in data/processed/ and a quality report.

Usage (from backend/):  python -m app.scripts.process_datasets
Originals in data/original/ are never modified.
"""
import json
import sys
from pathlib import Path

from app.config import settings
from app.services import dataset_cleaning as dc


def main(ehc_path: str | None = None, inbody_path: str | None = None) -> dict:
    ehc_path = Path(ehc_path or settings.EHC_FILE)
    inbody_path = Path(inbody_path or settings.INBODY_FILE)
    out_dir = Path(settings.PROCESSED_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    ehc, ehc_rep = dc.clean_ehc(dc.read_ehc(ehc_path))
    inb, inb_rep = dc.clean_inbody(dc.read_inbody(inbody_path))
    link = dc.analyse_linkage(ehc, inb)

    ehc.to_csv(out_dir / "ehc_clean.csv", index=False)
    inb.to_csv(out_dir / "inbody_clean.csv", index=False)
    report = {"ehc": ehc_rep, "inbody": inb_rep, "linkage": link,
              "units_assumed": dc.EHC_UNITS}
    (out_dir / "dataset_quality_report.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({"ehc_rows": len(ehc), "inbody_rows": len(inb), "linkage": link}, indent=2))
    return report


if __name__ == "__main__":
    main(*(sys.argv[1:3]))
