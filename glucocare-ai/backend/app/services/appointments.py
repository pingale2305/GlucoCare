"""Appointment slot rules: 40-minute Zoom slots, Monday-Saturday, with a lunch break."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.config import settings

ACTIVE = ("pending", "accepted", "reschedule_proposed")
HORIZON_DAYS = 60
MIN_NOTICE = timedelta(minutes=30)


def slot_starts(day: date) -> list[datetime]:
    if day.weekday() not in settings.APPT_DAYS:
        return []
    step = timedelta(minutes=settings.APPT_MINUTES)
    t = datetime.combine(day, time(settings.APPT_START_HOUR))
    end = datetime.combine(day, time(settings.APPT_END_HOUR))
    lunch_a = datetime.combine(day, time(settings.APPT_LUNCH_START))
    lunch_b = datetime.combine(day, time(settings.APPT_LUNCH_END))
    out = []
    while t + step <= end:
        if not (t < lunch_b and t + step > lunch_a):
            out.append(t)
        t += step
    return out


def is_valid_slot(dt: datetime, now: datetime | None = None) -> str | None:
    """None when the start time can be booked, otherwise the reason it cannot."""
    now = now or datetime.now()
    if dt not in slot_starts(dt.date()):
        return "Choose one of the listed time slots"
    if dt < now + MIN_NOTICE:
        return "That time has already passed or is too soon"
    if dt.date() > now.date() + timedelta(days=HORIZON_DAYS):
        return "Appointments can be booked up to 60 days ahead"
    return None
