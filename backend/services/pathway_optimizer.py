from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from ..tables.pathway import Pathway
from ..tables.course import Course
from ..tables.course_prerequisite import CoursePrerequisite
from ..tables.semester import Semester as SemesterModel
from ..tables.course_offering import CourseOffering


def _next_semester_label(current_label: str) -> str:
    # current_label expected like "Fall 2025"; rotate Fall->Spring->Summer->Fall
    try:
        term, year_s = current_label.split()
        year = int(year_s)
    except Exception:
        # fallback to current date
        now = datetime.now()
        month = now.month
        if month >= 8: term, year = "Fall", now.year
        elif month >= 5: term, year = "Summer", now.year
        else: term, year = "Spring", now.year

    order = ["Fall", "Spring", "Summer"]
    if term not in order:
        term = order[0]

    idx = order.index(term)
    next_idx = (idx + 1) % len(order)
    next_term = order[next_idx]
    next_year = year + 1 if next_term == "Fall" and next_idx == 0 and term == "Summer" else year
    # simpler: if moving from Fall->Spring increment year? many schools have Fall 2025 -> Spring 2026
    if term == "Fall" and next_term == "Spring":
        next_year = year + 1
    if term == "Spring" and next_term == "Summer":
        next_year = year
    if term == "Summer" and next_term == "Fall":
        next_year = year

    return f"{next_term} {next_year}"


def build_prereq_map(db: Session) -> Dict[str, Set[str]]:
    """Return mapping course_code -> set of prerequisite course_codes."""
    # Map course id -> course_code
    courses = db.query(Course).all()
    id_to_code = {c.id: c.course_code for c in courses}

    prereq_map: Dict[str, Set[str]] = {c.course_code: set() for c in courses}
    rels = db.query(CoursePrerequisite).all()
    for r in rels:
        course_code = id_to_code.get(r.course_id)
        prereq_code = id_to_code.get(r.prerequisite_id)
        if course_code and prereq_code:
            prereq_map.setdefault(course_code, set()).add(prereq_code)

    return prereq_map


def gather_pathway_courses(db: Session, pathway_id: Optional[int] = None, pathway_code: Optional[str] = None) -> List[Course]:
    if pathway_id is not None:
        pathway = db.query(Pathway).filter(Pathway.id == pathway_id).first()
    elif pathway_code is not None:
        pathway = db.query(Pathway).filter(Pathway.code == pathway_code).first()
    else:
        raise ValueError("Either pathway_id or pathway_code must be provided")

    if not pathway:
        return []

    course_set = set()
    # include pathway.courses and requirement courses if present
    if hasattr(pathway, 'courses') and pathway.courses:
        for c in pathway.courses:
            course_set.add(c.course_code)

    if hasattr(pathway, 'requirements') and pathway.requirements:
        for req in pathway.requirements:
            if hasattr(req, 'courses') and req.courses:
                for c in req.courses:
                    course_set.add(c.course_code)

    if not course_set:
        return []

    courses = db.query(Course).filter(Course.course_code.in_(list(course_set))).all()
    return courses


def optimize_pathway(
    db: Session,
    pathway_id: Optional[int] = None,
    pathway_code: Optional[str] = None,
    completed_course_codes: Optional[List[str]] = None,
    max_credits_per_semester: int = 15,
    start_semester: Optional[str] = None,
    max_terms: int = 12,
) -> List[Dict]:
    """Return a semester-by-semester plan of courses (list of dicts).

    This is a simple greedy scheduler that:
    - collects required courses from pathway
    - respects prerequisites (uses CoursePrerequisite table)
    - packs courses into semesters up to max_credits_per_semester
    - does not consider time conflicts or course offering frequency
    """
    completed = set((completed_course_codes or []))
    courses = gather_pathway_courses(db, pathway_id=pathway_id, pathway_code=pathway_code)
    if not courses:
        return []

    # map course_code -> Course
    code_to_course = {c.course_code: c for c in courses}

    # prereq map for all courses in DB
    prereq_map = build_prereq_map(db)

    # target set
    remaining = set(code_to_course.keys()) - completed

    # determine starting semester label
    if start_semester:
        sem_label = start_semester
    else:
        # try to use current semester from Semester table if available
        current = db.query(SemesterModel).filter(SemesterModel.start_date <= datetime.today(), SemesterModel.end_date >= datetime.today()).first()
        if current:
            sem_label = f"{current.term} {current.year}"
        else:
            # fallback: choose current term based on month
            today = datetime.today()
            if today.month >= 8:
                sem_label = f"Fall {today.year}"
            elif today.month >= 5:
                sem_label = f"Summer {today.year}"
            else:
                sem_label = f"Spring {today.year}"

    plan: List[Dict] = []
    term_count = 0

    def offered_this_term(code: str, sem_label: str) -> Optional[CourseOffering]:
        """Return a CourseOffering for the given course_code and sem_label, or None.

        sem_label expected as 'Term YYYY' (e.g., 'Fall 2025'). If CourseOffering.year is NULL it
        represents a recurring offering in that term. Preference: exact year match -> recurring.
        """
        try:
            term, year_s = sem_label.split()
            year = int(year_s)
        except Exception:
            # if parsing fails, only match term name
            term = sem_label
            year = None

        # find course id for code
        course = code_to_course.get(code)
        if not course:
            return None

        q = db.query(CourseOffering).filter(CourseOffering.course_id == course.id)

        # prefer exact year match if year provided
        if year is not None:
            offered_year = q.filter((CourseOffering.year == year) & (CourseOffering.term == term)).first()
            if offered_year:
                return offered_year

        # fallback to recurring offering (year NULL)
        offered_recurring = q.filter((CourseOffering.year == None) & (CourseOffering.term == term)).first()
        return offered_recurring


    while remaining and term_count < max_terms:
        term_count += 1
        # eligible: prerequisites subset of completed
        eligible = [code for code in remaining if prereq_map.get(code, set()).issubset(completed)]

        # filter by offerings for this term
        offered_now = [code for code in eligible if offered_this_term(code, sem_label)]

        # sort eligible by numeric level if possible (e.g., CSCI-1100 -> 1100), else by code
        def sort_key(code: str):
            parts = ''.join(ch if ch.isdigit() else ' ' for ch in code).split()
            return int(parts[0]) if parts else 0

        offered_now.sort(key=sort_key)

        semester_courses = []
        credits = 0
        for code in offered_now:
            c = code_to_course.get(code)
            if not c:
                continue
            if credits + (c.credits or 0) > max_credits_per_semester:
                continue
            offering = offered_this_term(code, sem_label)
            # offering should be present in offered_now, but double-check
            offering_info = None
            if offering:
                offering_info = {
                    'section': offering.section,
                    'days': offering.days,
                    'start_time': offering.start_time,
                    'end_time': offering.end_time,
                    'instructor': offering.instructor,
                    'location': offering.location,
                    'capacity': offering.capacity,
                }

            semester_courses.append({
                'course_code': code,
                'name': c.name,
                'credits': c.credits,
                'offering': offering_info,
            })
            credits += c.credits or 0

        # If no offered courses fit this semester but there are eligible courses, advance term
        if not semester_courses:
            # If there were no eligible courses at all, it's likely due to unmet prereqs; advance term
            # but avoid infinite loop: if nothing eligible (due to unmet prereqs) and no eligible courses
            # across all terms, break.
            if not eligible:
                # nothing eligible this turn; cannot progress -> break
                break
            # else, advance term and continue trying to schedule eligible courses later
            sem_label = _next_semester_label(sem_label)
            continue

        plan.append({'semester': sem_label, 'courses': semester_courses, 'total_credits': credits})

        # mark scheduled as completed and remove from remaining
        for sc in semester_courses:
            completed.add(sc['course_code'])
            if sc['course_code'] in remaining:
                remaining.remove(sc['course_code'])

        # advance to next semester label
        sem_label = _next_semester_label(sem_label)

    return plan
