"""Application settings, read from environment variables / the .env file.
No secrets are hard-coded: SECRET_KEY has no default and the app refuses to
start without one."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # glucocare-ai/


def _load_dotenv() -> None:
    for candidate in (ROOT / ".env", ROOT / "backend" / ".env"):
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _path(name: str, default: str) -> str:
    p = Path(os.environ.get(name, default))
    return str(p if p.is_absolute() else (ROOT / p).resolve())


class Settings:
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
    ACCESS_TOKEN_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_MINUTES", "480"))
    DATABASE_PATH: str = _path("DATABASE_PATH", "glucocare.db")
    UPLOAD_DIR: str = _path("UPLOAD_DIR", "uploads")
    REPORT_DIR: str = _path("REPORT_DIR", "generated_reports")
    MODEL_DIR: str = _path("MODEL_DIR", "models")
    PROCESSED_DIR: str = _path("PROCESSED_DIR", "data/processed")
    EHC_FILE: str = _path("EHC_FILE", "data/original/EHC_data_-_Dr_Dhaval.xls")
    INBODY_FILE: str = _path("INBODY_FILE", "data/original/inbody970_data_Excel_-_Dr_Dhaval.xlsx")
    APPT_START_HOUR: int = int(os.environ.get("APPT_START_HOUR", "10"))
    APPT_END_HOUR: int = int(os.environ.get("APPT_END_HOUR", "18"))
    APPT_LUNCH_START: int = int(os.environ.get("APPT_LUNCH_START", "13"))
    APPT_LUNCH_END: int = int(os.environ.get("APPT_LUNCH_END", "14"))
    APPT_MINUTES: int = 40
    APPT_DAYS = {0, 1, 2, 3, 4, 5}  # Monday-Saturday
    MAX_UPLOAD_MB: int = int(os.environ.get("MAX_UPLOAD_MB", "10"))
    ALLOWED_UPLOAD_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".csv"}
    CORS_ORIGINS: list[str] = [o.strip() for o in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
    # Used only by `python -m app.scripts.seed` to create the first doctor account.
    DOCTOR_EMAIL: str = os.environ.get("DOCTOR_EMAIL", "")
    DOCTOR_PASSWORD: str = os.environ.get("DOCTOR_PASSWORD", "")
    DOCTOR_NAME: str = os.environ.get("DOCTOR_NAME", "Dr. Dhaval")

    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite:///{self.DATABASE_PATH}"

    def require_secret(self) -> None:
        if len(self.SECRET_KEY) < 32:
            raise RuntimeError(
                "SECRET_KEY is missing or shorter than 32 characters. Copy .env.example to .env "
                "(or run scripts\\setup.ps1) so a random key is generated.")


settings = Settings()
