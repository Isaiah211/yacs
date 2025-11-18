from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from ..tables.pathway import Pathway
from ..tables.course import Course
from ..tables.course_prerequisite import CoursePrerequisite
from ..tables.semester import Semester as SemesterModel
from ..tables.course_offering import CourseOffering
from ..tables.student_preferences import StudentPreferences


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
    allow_overfull: bool = False,
    reserve_seats: bool = False,
    balance_load: bool = False,
    user_id: Optional[int] = None,
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

    # Helper: parse days/time and detect conflicts (shared by both scheduling modes)
    def parse_days(days: Optional[str]) -> Set[str]:
        if not days:
            return set()
        ds = set()
        s = days.strip().upper()
        if 'TR' in s:
            s = s.replace('TR', 'R')
        for ch in s:
            if ch in ('M', 'T', 'W', 'R', 'F', 'S', 'U'):
                ds.add(ch)
        return ds

    def parse_time(tm: Optional[str]) -> Optional[int]:
        if not tm:
            return None
        t = tm.strip().upper()
        try:
            if 'AM' in t or 'PM' in t:
                meridian = 'AM' if 'AM' in t else 'PM'
                tnum = t.replace('AM', '').replace('PM', '').strip()
                parts = tnum.split(':')
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                if meridian == 'PM' and hour != 12:
                    hour += 12
                if meridian == 'AM' and hour == 12:
                    hour = 0
                return hour * 60 + minute
            else:
                parts = t.split(':')
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                return hour * 60 + minute
        except Exception:
            return None

    def times_conflict(a: CourseOffering, b: CourseOffering) -> bool:
        days_a = parse_days(a.days)
        days_b = parse_days(b.days)
        if not days_a or not days_b:
            return False
        if days_a.isdisjoint(days_b):
            return False
        a_s = parse_time(a.start_time)
        a_e = parse_time(a.end_time)
        b_s = parse_time(b.start_time)
        b_e = parse_time(b.end_time)
        if a_s is None or a_e is None or b_s is None or b_e is None:
            return False
        return not (a_e <= b_s or b_e <= a_s)

    # Load student preferences if provided
    preferences = None
    if user_id is not None:
        preferences = db.query(StudentPreferences).filter(StudentPreferences.user_id == user_id).first()
    # interpret preferences
    pref_max_credits = None
    pref_unavailable_days: Set[str] = set()
    pref_avoid_mornings = False
    pref_avoid_evenings = False
    pref_instructors: Set[str] = set()
    if preferences:
        if preferences.max_credits_per_term:
            pref_max_credits = preferences.max_credits_per_term
        if preferences.unavailable_days:
            pref_unavailable_days = parse_days(preferences.unavailable_days)
        pref_avoid_mornings = bool(preferences.avoid_mornings)
        pref_avoid_evenings = bool(preferences.avoid_evenings)
        if preferences.preferred_instructors:
            pref_instructors = set([s.strip().lower() for s in (preferences.preferred_instructors or '').split(',') if s.strip()])
    # effective per-term cap
    eff_max_credits = pref_max_credits or max_credits_per_semester

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

        # collect offerings for this term (exact year + recurring)
        candidates = []
        if year is not None:
            candidates.extend(q.filter((CourseOffering.year == year) & (CourseOffering.term == term)).all())
        candidates.extend(q.filter((CourseOffering.year == None) & (CourseOffering.term == term)).all())

        if not candidates:
            return None
        # prefer an offering with available seats
        # also prefer offerings that match preferred instructors if provided
        def instructor_score(off: CourseOffering) -> int:
            if not pref_instructors:
                return 0
            inst = (off.instructor or '').strip().lower()
            return 1 if inst in pref_instructors else 0

        # prefer an offering with available seats
        # sort candidates by (has_space desc, instructor_pref desc)
        def has_space(off: CourseOffering) -> int:
            if off.capacity is None:
                return 1
            if off.enrolled is None:
                return 1
            return 1 if off.enrolled < off.capacity else 0

        candidates.sort(key=lambda off: (has_space(off), instructor_score(off)), reverse=True)
        # return the top candidate if it has space or allow_overfull is True
        top = candidates[0]
        if has_space(top) or allow_overfull:
            return top

        # if none have space, allow overfull if requested (return first candidate marked full)
        if allow_overfull:
            return candidates[0]

        return None


    if not balance_load:
        # Greedy per-term scheduling: for each term pick a non-conflicting set
        # of offerings up to the per-term credit cap.
        while remaining and term_count < max_terms:
            term_count += 1
            eligible = [code for code in remaining if prereq_map.get(code, set()).issubset(completed)]

            # find offerings for eligible courses
            offered_now_with_offering = []
            for code in eligible:
                offering = offered_this_term(code, sem_label)
                if offering:
                    offered_now_with_offering.append((code, offering))

            # prepare candidates: (code, offering, credits)
            candidates = []
            for code, offering in offered_now_with_offering:
                c = code_to_course.get(code)
                if not c:
                    continue
                # apply preferences: skip offerings on unavailable days
                if pref_unavailable_days:
                    off_days = parse_days(offering.days)
                    if not off_days.isdisjoint(pref_unavailable_days):
                        continue
                # avoid mornings/evenings if requested
                st = parse_time(offering.start_time)
                if pref_avoid_mornings and st is not None and st < 10 * 60:
                    continue
                if pref_avoid_evenings and st is not None and st >= 18 * 60:
                    continue
                is_full = (offering.capacity is not None and offering.enrolled is not None and offering.enrolled >= offering.capacity)
                if is_full and not allow_overfull:
                    continue
                # boost credit value slightly if instructor preferred (used by sort in some branches)
                bonus = 0
                if pref_instructors:
                    inst = (offering.instructor or '').strip().lower()
                    if inst in pref_instructors:
                        bonus = 0.1
                candidates.append((code, offering, (c.credits or 0) + bonus))

            # select non-conflicting subset maximizing credits up to cap
            selected = []
            if candidates:
                candidates.sort(key=lambda tup: tup[2], reverse=True)
                best_set: List[tuple] = []
                best_credit = 0
                n = len(candidates)

                def dfs(idx: int, cur: List[tuple], cur_credit: int):
                    nonlocal best_set, best_credit
                    if cur_credit > best_credit:
                        best_set = cur.copy()
                        best_credit = cur_credit
                    if idx >= n:
                        return
                    for j in range(idx, n):
                        code_j, off_j, cred_j = candidates[j]
                        if cur_credit + cred_j > eff_max_credits:
                            continue
                        conflict = False
                        for (_, off_k, _) in cur:
                            if times_conflict(off_j, off_k):
                                conflict = True
                                break
                        if conflict:
                            continue
                        cur.append((code_j, off_j, cred_j))
                        dfs(j + 1, cur, cur_credit + cred_j)
                        cur.pop()

                dfs(0, [], 0)
                selected = best_set

            semester_courses = []
            credits = 0
            for code, offering, cred in selected:
                c = code_to_course.get(code)
                if not c:
                    continue
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
                if offering_info['status'] == 'full' and not allow_overfull:
                    continue
                if reserve_seats and offering.enrolled is not None:
                    offering.enrolled = offering.enrolled + 1
                semester_courses.append({
                    'course_code': code,
                    'name': c.name,
                    'credits': c.credits,
                    'offering': offering_info,
                })
                credits += c.credits or 0

            # If no offered courses fit this semester but there are eligible courses, advance term
            if not semester_courses:
                if not eligible:
                    break
                sem_label = _next_semester_label(sem_label)
                continue

            plan.append({'semester': sem_label, 'courses': semester_courses, 'total_credits': credits})

            # mark scheduled as completed and remove from remaining
            for sc in semester_courses:
                completed.add(sc['course_code'])
                if sc['course_code'] in remaining:
                    remaining.remove(sc['course_code'])

            sem_label = _next_semester_label(sem_label)
        return plan

    # --- load balancing mode: try to spread credits evenly across all terms ---
    # Precompute all eligible courses by term, then assign in round-robin fashion
    # This is a greedy heuristic: for each term, pick from eligible, non-conflicting, not-yet-scheduled courses, aiming for target_credits per term
    plan = []
    scheduled = set(completed)
    sem_label = start_semester
    if not sem_label:
        current = db.query(SemesterModel).filter(SemesterModel.start_date <= datetime.today(), SemesterModel.end_date >= datetime.today()).first()
        if current:
            sem_label = f"{current.term} {current.year}"
        else:
            today = datetime.today()
            if today.month >= 8:
                sem_label = f"Fall {today.year}"
            elif today.month >= 5:
                sem_label = f"Summer {today.year}"
            else:
                sem_label = f"Spring {today.year}"

    # Compute target credits per term (respect preferences)
    total_credits = sum(c.credits or 0 for c in code_to_course.values() if c.course_code not in completed)
    n_terms = max_terms
    target_credits = eff_max_credits
    if n_terms > 0:
        target_credits = min(eff_max_credits, max(1, (total_credits + n_terms - 1) // n_terms))

    # For each term, try to pack up to target_credits, round-robin until all scheduled or terms exhausted
    for t in range(n_terms):
        # eligible: prereqs met and not yet scheduled
        eligible = [code for code in code_to_course if code not in scheduled and prereq_map.get(code, set()).issubset(scheduled)]
        # filter by offerings for this term and select offering
        offered_now_with_offering = []
        for code in eligible:
            offering = offered_this_term(code, sem_label)
            if offering:
                offered_now_with_offering.append((code, offering))
        # prepare candidates: (code, offering, credits)
        candidates = []
        for code, offering in offered_now_with_offering:
            c = code_to_course.get(code)
            if not c:
                continue
            # apply preferences
            if pref_unavailable_days:
                off_days = parse_days(offering.days)
                if not off_days.isdisjoint(pref_unavailable_days):
                    continue
            st = parse_time(offering.start_time)
            if pref_avoid_mornings and st is not None and st < 10 * 60:
                continue
            if pref_avoid_evenings and st is not None and st >= 18 * 60:
                continue
            is_full = (offering.capacity is not None and offering.enrolled is not None and offering.enrolled >= offering.capacity)
            if is_full and not allow_overfull:
                continue
            bonus = 0
            if pref_instructors:
                inst = (offering.instructor or '').strip().lower()
                if inst in pref_instructors:
                    bonus = 0.1
            candidates.append((code, offering, (c.credits or 0) + bonus))
        # backtracking selection to maximize credits while avoiding time conflicts
        selected = []
        if candidates:
            candidates.sort(key=lambda tup: tup[2], reverse=True)
            best_set = []
            best_credit = 0
            n = len(candidates)
            def dfs(idx: int, cur: List[tuple], cur_credit: int):
                nonlocal best_set, best_credit
                if cur_credit > best_credit and cur_credit <= target_credits:
                    best_set = cur.copy()
                    best_credit = cur_credit
                if idx >= n:
                    return
                for j in range(idx, n):
                    code_j, off_j, cred_j = candidates[j]
                    if cur_credit + cred_j > target_credits:
                        continue
                    conflict = False
                    for (_, off_k, _) in cur:
                        if times_conflict(off_j, off_k):
                            conflict = True
                            break
                    if conflict:
                        continue
                    cur.append((code_j, off_j, cred_j))
                    dfs(j + 1, cur, cur_credit + cred_j)
                    cur.pop()
            dfs(0, [], 0)
            selected = best_set
        semester_courses = []
        credits = 0
        for code, offering, cred in selected:
            c = code_to_course.get(code)
            if not c:
                continue
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
            if offering_info['status'] == 'full' and not allow_overfull:
                continue
            if reserve_seats and offering.enrolled is not None:
                offering.enrolled = offering.enrolled + 1
            semester_courses.append({
                'course_code': code,
                'name': c.name,
                'credits': c.credits,
                'offering': offering_info,
            })
            credits += c.credits or 0
            scheduled.add(code)
        plan.append({'semester': sem_label, 'courses': semester_courses, 'total_credits': credits})
        sem_label = _next_semester_label(sem_label)
    return plan
