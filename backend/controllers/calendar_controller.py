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

def _render_event_lines(course: Course, semester: Optional[Semester]) -> Optional[List[str]]:
    #convert a course row into ics vevent lines
    days = _normalize_days(course.days_of_week or "")
    start_time = _coerce_time(course.start_time)
    end_time = _coerce_time(course.end_time)

    if not days or not start_time or not end_time:
        #insufficient data
        return None

    start_date = semester.start_date if semester and semester.start_date else date.today()
    end_date = semester.end_date if semester and semester.end_date else start_date + timedelta(days=DEFAULT_TERM_LENGTH_DAYS)

    #guard against inverted ranges
    if end_date < start_date:
        end_date = start_date

    first_event_date: Optional[date] = None
    ical_days: List[str] = []

    for day_code in days:
        ical_code, weekday = DAY_CODE_MAP[day_code]
        ical_days.append(ical_code)
        candidate_date = _first_occurrence(start_date, weekday)
        if first_event_date is None or candidate_date < first_event_date:
            first_event_date = candidate_date

    if not first_event_date:
        return None

    dt_start = datetime.combine(first_event_date, start_time)
    dt_end = datetime.combine(first_event_date, end_time)
    until_dt = datetime.combine(end_date, end_time)

    summary = f"{course.course_code or 'COURSE'} - {course.name or 'Class'}"
    description_parts = [f"Instructor: {course.instructor or 'TBA'}", f"Credits: {course.credits}" ]
    if course.description:
        description_parts.append(course.description)
    description = "\\n".join(description_parts)

    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    uid = f"{course.course_code or 'course'}-{course.id}-{uuid.uuid4().hex}@yacs"

    event_lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_stamp}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"DTSTART:{_format_dt(dt_start)}",
        f"DTEND:{_format_dt(dt_end)}",
    ]

    if course.location:
        event_lines.append(f"LOCATION:{course.location}")

    if ical_days:
        event_lines.append(
            "RRULE:FREQ=WEEKLY;BYDAY=" + ",".join(ical_days) + f";UNTIL:{_format_dt(until_dt)}"
        )

    event_lines.append("END:VEVENT")
    return event_lines


def build_calendar_export(db: Session, *, course_ids: Optional[List[int]] = None, course_codes: Optional[List[str]] = None, semester: Optional[str] = None, calendar_name: str = "Course Schedule", timezone: str = "America/New_York") -> Dict:
    #generate an ics calendar for the selected courses
    if not course_ids and not course_codes:
        return {"success": False, "error": "provide course_ids or course_codes"}

    query = db.query(Course)

    if course_ids:
        query = query.filter(Course.id.in_(course_ids))

    if course_codes:
        query = query.filter(Course.course_code.in_(course_codes))
        if semester:
            query = query.filter(Course.semester == semester)

    courses = query.all()

    if not courses:
        return {"success": False, "error": "No courses matched the provided filters."}

    semester_names = {c.semester for c in courses if c.semester}
    semester_map: Dict[str, Semester] = {}
    if semester_names:
        semester_rows = db.query(Semester).filter(Semester.name.in_(semester_names)).all()
        semester_map = {row.name: row for row in semester_rows}

    calendar_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//YACS//Calendar Export//EN",
        f"X-WR-CALNAME:{calendar_name}",
        f"X-WR-TIMEZONE:{timezone}",
        f"X-WR-CALDESC:Exported from YACS on {datetime.utcnow().isoformat()}",
    ]

    skipped: List[str] = []
    exported_count = 0

    for course in courses:
        event_lines = _render_event_lines(course, semester_map.get(course.semester))
        if not event_lines:
            skipped.append(course.course_code or str(course.id))
            continue
        calendar_lines.extend(event_lines)
        exported_count += 1

    calendar_lines.append("END:VCALENDAR")

    if exported_count == 0:
        return {
            "success": False,
            "error": "None of the selected courses include meeting days and times to export.",
            "skipped": skipped,
        }

    content = "\r\n".join(calendar_lines) + "\r\n"
    filename = f"{_slugify(calendar_name)}-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.ics"

    return {
        "success": True,
        "ics": content,
        "filename": filename,
        "metadata": {
            "exported": exported_count,
            "skipped": skipped,
            "total_requested": len(courses),
        }
    }
