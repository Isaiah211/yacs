from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta, time
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..tables.course import Course
from ..tables.semester import Semester

#map letter day abbreviations to iCalendar weekday codes
DAY_CODE_MAP = {
    "M": ("MO", 0),
    "T": ("TU", 1),
    "W": ("WE", 2),
    "R": ("TH", 3),
    "F": ("FR", 4),
    "S": ("SA", 5),
    "U": ("SU", 6) #sunday when denoted as U
}

DEFAULT_TERM_LENGTH_DAYS = 100 #fallback length if semester dates missing


def _slugify(value: str) -> str:
    #create filesystem friendly slug for calendar filenames
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value or "yacs-calendar").strip("-")
    return (cleaned or "yacs-calendar").lower()


def _normalize_days(days: str) -> List[str]:
    #return deduplicated day codes while preserving original order
    ordered: List[str] = []
    seen = set()
    for ch in (days or "").upper():
        if ch in DAY_CODE_MAP and ch not in seen:
            ordered.append(ch)
            seen.add(ch)
    return ordered


def _first_occurrence(start: date, weekday: int) -> date:
    offset = (weekday - start.weekday()) % 7
    return start + timedelta(days=offset)


def _format_dt(dt_value: datetime) -> str:
    return dt_value.strftime("%Y%m%dT%H%M%S")


def _coerce_time(value) -> Optional[time]:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        try:
            parts = [int(p) for p in value.split(":")]
            while len(parts) < 3:
                parts.append(0)
            return time(parts[0], parts[1], parts[2])
        except (ValueError, TypeError):
            return None
    return None
