"""Pydantic request schemas (input validation)."""
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

import re

from pydantic import BaseModel, Field, field_validator

# Plain format check (pydantic's EmailStr rejects reserved domains such as ".local")
EmailStr = Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)]

HEIGHT = dict(ge=50, le=250)
WEIGHT = dict(ge=10, le=400)


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    sex: Literal["M", "F"] | None = None
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, max_length=30)
    height_cm: float | None = Field(default=None, **HEIGHT)
    weight_kg: float | None = Field(default=None, **WEIGHT)

    @field_validator("date_of_birth")
    @classmethod
    def dob_sane(cls, v):
        if v and (v > date.today() or v.year < 1900):
            raise ValueError("Invalid date of birth")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    role: Literal["doctor", "patient"] | None = None


class BodyIn(BaseModel):
    height_cm: float = Field(**HEIGHT)
    weight_kg: float = Field(**WEIGHT)


class GlucoseIn(BaseModel):
    measured_at: datetime
    value_mg_dl: float = Field(ge=20, le=600)
    context: Literal["fasting", "post_meal", "random", "bedtime"] = "random"

    @field_validator("measured_at")
    @classmethod
    def not_future(cls, v):
        v = v.replace(tzinfo=None)
        if v > datetime.now() + timedelta(hours=15):
            raise ValueError("Reading time cannot be in the future")
        return v


class FoodIn(BaseModel):
    entry_date: date
    meal_type: Literal["Breakfast", "Lunch", "Snacks", "Dinner"]
    items: str = Field(min_length=2, max_length=500)

    @field_validator("entry_date")
    @classmethod
    def not_future(cls, v):
        if v > date.today() + timedelta(days=1):
            raise ValueError("Date cannot be in the future")
        return v

    @field_validator("items")
    @classmethod
    def strip_items(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Enter the food items")
        return v


class StepsIn(BaseModel):
    entry_date: date
    steps: int = Field(ge=0, le=100000)

    @field_validator("entry_date")
    @classmethod
    def not_future(cls, v):
        if v > date.today() + timedelta(days=1):
            raise ValueError("Date cannot be in the future")
        return v


class SuggestionIn(BaseModel):
    content: str = Field(min_length=3, max_length=4000)
    suggestion_date: date | None = None

    @field_validator("content")
    @classmethod
    def strip_content(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Write the suggestion")
        return v


class AlertReviewIn(BaseModel):
    comment: str | None = Field(default=None, max_length=500)


class ManualLabIn(BaseModel):
    collected_on: date
    hba1c: float | None = Field(default=None, ge=3, le=20)
    fbs: float | None = Field(default=None, ge=20, le=700)
    ppbs: float | None = Field(default=None, ge=20, le=900)
    total_cholesterol: float | None = Field(default=None, ge=50, le=600)
    ldl: float | None = Field(default=None, ge=10, le=500)
    hdl: float | None = Field(default=None, ge=5, le=150)
    triglycerides: float | None = Field(default=None, ge=20, le=2000)
    sgot: float | None = Field(default=None, ge=1, le=3000)
    sgpt: float | None = Field(default=None, ge=1, le=3000)
    ggtp: float | None = Field(default=None, ge=1, le=3000)
    creatinine: float | None = Field(default=None, ge=0.1, le=20)
    egfr: float | None = Field(default=None, ge=1, le=200)
    urine_acr: float | None = Field(default=None, ge=0, le=5000)

    @field_validator("collected_on")
    @classmethod
    def not_future(cls, v):
        if v > date.today() + timedelta(days=1):
            raise ValueError("Date cannot be in the future")
        return v


_ZOOM = re.compile(r"^https://([\w-]+\.)*zoom\.(us|com)/\S+$", re.I)


def _zoom(v: str) -> str:
    v = v.strip()
    if not _ZOOM.match(v):
        raise ValueError("Enter a valid Zoom link (https://...zoom.us/j/...)")
    return v


class BookIn(BaseModel):
    start_at: datetime
    reason: str | None = Field(default=None, max_length=300)


class AcceptIn(BaseModel):
    zoom_url: str = Field(max_length=300)

    @field_validator("zoom_url")
    @classmethod
    def check_zoom(cls, v):
        return _zoom(v)


class ProposeIn(BaseModel):
    start_at: datetime
    zoom_url: str = Field(max_length=300)

    @field_validator("zoom_url")
    @classmethod
    def check_zoom(cls, v):
        return _zoom(v)


class RespondIn(BaseModel):
    action: Literal["accept", "decline"]
