from typing import List, Dict, Optional, Set
from sqlalchemy.orm import Session
from datetime import datetime

from ortools.sat.python import cp_model

from ..tables.course import Course
from ..tables.course_prerequisite import CoursePrerequisite
from ..tables.semester import Semester as SemesterModel
from ..tables.course_offering import CourseOffering


def _next_sem_label(label: str) -> str:
    parts = label.split()
    if len(parts) >= 2:
        term = parts[0]
        try:
            year = int(parts[1])
        except Exception:
            year = None
    else:
        term = 'Fall'
        year = datetime.today().year
    order = ['Fall', 'Spring', 'Summer']
    if term not in order:
        term = 'Fall'
    idx = order.index(term)
    next_idx = (idx + 1) % len(order)
    next_term = order[next_idx]
    next_year = year
    if term == 'Fall' and next_term == 'Spring' and year is not None:
        next_year = year + 1
    return f"{next_term} {next_year}"


def build_prereq_map(db: Session) -> Dict[str, Set[str]]:
    courses = db.query(Course).all()
    id_to_code = {c.id: c.course_code for c in courses}
    prereq_map = {c.course_code: set() for c in courses}
    rels = db.query(CoursePrerequisite).all()
    for r in rels:
        course_code = id_to_code.get(r.course_id)
        prereq_code = id_to_code.get(r.prerequisite_id)
        if course_code and prereq_code:
            prereq_map.setdefault(course_code, set()).add(prereq_code)
    return prereq_map


def optimize_pathway_exact(
    db: Session,
    pathway_courses: List[Course],
    prereq_map: Dict[str, Set[str]],
    completed: Set[str],
    start_semester: Optional[str],
    max_terms: int,
    max_credits_per_semester: int,
    allow_overfull: bool = False,
    timeout_seconds: int = 20,
) -> List[Dict]:
    """Use CP-SAT to solve the course-term assignment problem globally.
    Returns the same plan format as heuristic optimizer.
    This implementation makes simplifying assumptions:
    - Course can only be scheduled in terms where at least one offering exists (respecting allow_overfull)
    - Time/section conflicts are not modeled at offering level (future improvement)
    - Capacities are considered by testing if any offering in that term has space; does not reserve seats
    """
    # Map course_code -> Course
    code_to_course = {c.course_code: c for c in pathway_courses}
    remaining_codes = [code for code in code_to_course if code not in completed]
    if not remaining_codes:
        return []

    # build term labels
    if start_semester:
        sem0 = start_semester
    else:
        current = db.query(SemesterModel).filter(SemesterModel.start_date <= datetime.today(), SemesterModel.end_date >= datetime.today()).first()
        if current:
            sem0 = f"{current.term} {current.year}"
        else:
            today = datetime.today()
            if today.month >= 8:
                sem0 = f"Fall {today.year}"
            elif today.month >= 5:
                sem0 = f"Summer {today.year}"
            else:
                sem0 = f"Spring {today.year}"

    terms = [sem0]
    for i in range(1, max_terms):
        terms.append(_next_sem_label(terms[-1]))

    # availability: course x term -> bool if any offering exists and (has space or allow_overfull)
    availability = {code: [False] * len(terms) for code in remaining_codes}
    for ti, sem_label in enumerate(terms):
        try:
            term_name, year_s = sem_label.split()
            year = int(year_s)
        except Exception:
            term_name = sem_label
            year = None
        for code in remaining_codes:
            course = code_to_course.get(code)
            if not course:
                continue
            q = db.query(CourseOffering).filter(CourseOffering.course_id == course.id)
            cand = []
            if year is not None:
                cand.extend(q.filter((CourseOffering.year == year) & (CourseOffering.term == term_name)).all())
            cand.extend(q.filter((CourseOffering.year == None) & (CourseOffering.term == term_name)).all())
            if not cand:
                availability[code][ti] = False
            else:
                ok = False
                for off in cand:
                    if off.capacity is None:
                        ok = True
                        break
                    enrolled = off.enrolled or 0
                    if off.enrolled is None or enrolled < off.capacity:
                        ok = True
                        break
                if ok or allow_overfull:
                    availability[code][ti] = True

    # CP-SAT model
    model = cp_model.CpModel()
    x = {}
    for i, code in enumerate(remaining_codes):
        for t in range(len(terms)):
            if availability[code][t]:
                x[(code, t)] = model.NewBoolVar(f"x_{code}_{t}")
            else:
                # not available, skip creating var
                pass

    # each course at most once
    for code in remaining_codes:
        vars_for_code = [v for (c, t), v in x.items() if c == code]
        if vars_for_code:
            model.Add(sum(vars_for_code) <= 1)

    # prerequisites: for c with prereqs P, x_c_t <= sum_{s<t} x_p_s
    for code in remaining_codes:
        prereqs = prereq_map.get(code, set())
        prereqs = [p for p in prereqs if p in remaining_codes or p in code_to_course]
        if not prereqs:
            continue
        for t in range(len(terms)):
            var_c_t = x.get((code, t))
            if not var_c_t:
                continue
            # sum prereq taken before t
            prereq_vars = []
            for p in prereqs:
                for s in range(0, t):
                    v = x.get((p, s))
                    if v:
                        prereq_vars.append(v)
            if prereq_vars:
                model.Add(var_c_t <= sum(prereq_vars))
            else:
                # no way to satisfy prereq before t -> disallow scheduling at t
                model.Add(var_c_t == 0)

    # credits per term <= cap
    for t in range(len(terms)):
        term_vars = []
        coeffs = []
        for code in remaining_codes:
            v = x.get((code, t))
            if v:
                term_vars.append(v)
                coeffs.append(int(code_to_course[code].credits or 0))
        if term_vars:
            model.Add(sum(v * c for v, c in zip(term_vars, coeffs)) <= max_credits_per_semester)

    # objective: minimize weighted sum of term indices * credits (encourage earlier scheduling)
    obj_terms = []
    obj_coeffs = []
    for (code, t), var in x.items():
        weight = t  # earlier terms have smaller weight
        credit = int(code_to_course[code].credits or 0)
        obj_terms.append(var)
        obj_coeffs.append(weight * credit)
    if obj_terms:
        model.Minimize(sum(var * coeff for var, coeff in zip(obj_terms, obj_coeffs)))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(timeout_seconds)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return []

    # build plan
    plan = []
    scheduled = set()
    for t, sem_label in enumerate(terms):
        semester_courses = []
        credits = 0
        for code in remaining_codes:
            var = x.get((code, t))
            if var and solver.Value(var) == 1:
                c = code_to_course.get(code)
                # pick an offering for this term using simple preference logic
                offering = None
                try:
                    term_name, year_s = sem_label.split()
                    year = int(year_s)
                except Exception:
                    term_name = sem_label
                    year = None
                q = db.query(CourseOffering).filter(CourseOffering.course_id == c.id)
                candidates = []
                if year is not None:
                    candidates.extend(q.filter((CourseOffering.year == year) & (CourseOffering.term == term_name)).all())
                candidates.extend(q.filter((CourseOffering.year == None) & (CourseOffering.term == term_name)).all())
                if candidates:
                    offering = candidates[0]

                offering_info = None
                if offering:
                    offering_info = {
                        'id': offering.id,
                        'section': offering.section,
                        'days': offering.days,
                        'start_time': offering.start_time,
                        'end_time': offering.end_time,
                        'instructor': offering.instructor,
                        'location': offering.location,
                        'capacity': offering.capacity,
                        'enrolled': offering.enrolled,
                        'status': 'confirmed' if (offering.capacity is None or (offering.enrolled is None or offering.enrolled < offering.capacity)) else 'full',
                    }
                semester_courses.append({'course_code': code, 'name': c.name, 'credits': c.credits, 'offering': offering_info})
                credits += c.credits or 0
                scheduled.add(code)
        plan.append({'semester': sem_label, 'courses': semester_courses, 'total_credits': credits})
    return plan
