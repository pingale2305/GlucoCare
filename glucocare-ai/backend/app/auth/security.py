"""Password hashing (PBKDF2-HMAC-SHA256, stdlib) and JWT helpers."""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

_ITER = 260_000
ALGO = "HS256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITER).hex()
    return f"pbkdf2_sha256${_ITER}${salt}${dk}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, it, salt, dk = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(it)).hex()
        return hmac.compare_digest(calc, dk)
    except Exception:
        return False


def password_problem(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one digit."
    return None


def create_access_token(user_id: int, role: str) -> str:
    settings.require_secret()
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, settings.SECRET_KEY, algorithm=ALGO)


def decode_token(token: str) -> dict:
    settings.require_secret()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])


def hash_claim_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()
