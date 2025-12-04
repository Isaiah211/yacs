from typing import List, Dict, Any, Optional
from datetime import datetime, time
from types import SimpleNamespace


def _to_time_obj(t) -> Optional[time]:
    if t is None:
        return None
    if isinstance(t, time):
        return t
    if isinstance(t, str):
        # expect HH:MM:SS or HH:MM
        parts = t.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        s = int(parts[2]) if len(parts) > 2 else 0
        return time(h, m, s)
    return None


def has_day_overlap(days1: str, days2: str) -> bool:
    if not days1 or not days2:
        return False
    return bool(set(days1.upper()) & set(days2.upper()))


def has_time_overlap(start1, end1, start2, end2) -> bool:
    start1 = _to_time_obj(start1)
    end1 = _to_time_obj(end1)
    start2 = _to_time_obj(start2)
    end2 = _to_time_obj(end2)
    if not all([start1, end1, start2, end2]):
        return False
    return start1 < end2 and start2 < end1


def minutes_between(t1, t2) -> int:
    t1 = _to_time_obj(t1)
    t2 = _to_time_obj(t2)
    if not t1 or not t2:
        return 0
    dt1 = datetime.combine(datetime.today(), t1)
    dt2 = datetime.combine(datetime.today(), t2)
    return int((dt2 - dt1).total_seconds() // 60)


def score_courses(courses: List[Any], weights: Optional[Dict[str, float]] = None, db=None, preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Score a list of course-like objects. Each course should have attributes:
      - id, course_code, days_of_week, start_time, end_time

    Returns a dict with numeric score and breakdown.
    """
    if weights is None:
        # Tuned defaults:
        # - very large penalty for conflicts to prioritize conflict-free schedules
        # - moderately small penalty per-minute gap (encourages compact schedules but not too harsh)
        # - larger rating weight to prefer higher-rated course combinations
        # - day_penalty penalizes schedules spread over many distinct days
        # - compactness_reward gives extra score for schedules using fewer distinct days
        weights = {
            'conflict_penalty': 1000.0,
            'gap_penalty_per_minute': 0.5,
            'rating_weight': 20.0,
            'day_penalty_per_day': 75.0,
            'compactness_reward': 50.0,
            'base': 500.0
        }

    # detect conflicts
    conflicts = []
    for i in range(len(courses)):
        for j in range(i + 1, len(courses)):
            c1 = courses[i]
            c2 = courses[j]
            if c1.id == c2.id:
                continue
            # require same semester if attribute present
            if getattr(c1, 'semester', None) and getattr(c2, 'semester', None) and c1.semester != c2.semester:
                continue
            if not (getattr(c1, 'days_of_week', None) and getattr(c1, 'start_time', None) and getattr(c1, 'end_time', None)):
                continue
            if not (getattr(c2, 'days_of_week', None) and getattr(c2, 'start_time', None) and getattr(c2, 'end_time', None)):
                continue

            if has_day_overlap(c1.days_of_week, c2.days_of_week) and has_time_overlap(c1.start_time, c1.end_time, c2.start_time, c2.end_time):
                overlapping_days = set(c1.days_of_week.upper()) & set(c2.days_of_week.upper())
                conflicts.append({'course1': c1.course_code, 'course2': c2.course_code, 'days': ''.join(sorted(overlapping_days))})

    conflict_count = len(conflicts)

    # compute total gaps per day
    weekdays = list('MTWRFS')
    total_gaps_minutes = 0
    for day in weekdays:
        day_courses = [c for c in courses if c.days_of_week and day in c.days_of_week.upper() and c.start_time and c.end_time]
        if not day_courses:
            continue
        # sort by start_time
        def start_key(c):
            t = _to_time_obj(c.start_time)
            return t or time(0, 0)

        day_courses.sort(key=start_key)
        for a, b in zip(day_courses, day_courses[1:]):
            gap = minutes_between(a.end_time, b.start_time)
            if gap > 0:
                total_gaps_minutes += gap

    # compute average rating across courses if db available
    avg_rating = None
    rating_sum = 0.0
    rating_count = 0
    if db is not None:
        from tables.course_review import CourseReview
        from sqlalchemy import func
        for c in courses:
            r = db.query(func.avg(CourseReview.rating)).filter(CourseReview.course_id == c.id).scalar()
            if r:
                rating_sum += float(r)
                rating_count += 1
        if rating_count:
            avg_rating = rating_sum / rating_count

    # normalize preferences dict
    prefs = preferences or {}
    # if preferences contains SQLAlchemy object with to_dict, normalize
    if hasattr(prefs, 'to_dict'):
        try:
            prefs = prefs.to_dict()
        except Exception:
            prefs = dict()

    avoid_mornings = bool(prefs.get('avoid_mornings', False))
    avoid_evenings = bool(prefs.get('avoid_evenings', False))
    unavailable_days = (prefs.get('unavailable_days') or '')
    preferred_instructors = set([s.strip().lower() for s in (prefs.get('preferred_instructors') or []) if s and s.strip()]) if isinstance(prefs.get('preferred_instructors'), list) else set([s.strip().lower() for s in (prefs.get('preferred_instructors') or '').split(',') if s.strip()])

    # additional metric: distinct days used
    all_days = set()
    for c in courses:
        if getattr(c, 'days_of_week', None):
            all_days |= set(getattr(c, 'days_of_week').upper())
    # only count typical weekday letters
    valid_days = set('MTWRF')
    distinct_days = len(all_days & valid_days)

    # scoring formula
    score = weights.get('base', 0.0)
    score -= conflict_count * weights.get('conflict_penalty', 100.0)
    score -= total_gaps_minutes * weights.get('gap_penalty_per_minute', 1.0)
    # penalize spread across many days
    score -= distinct_days * weights.get('day_penalty_per_day', 0.0)
    # reward compactness (fewer days) relative to a 5-day baseline
    max_days = 5
    compactness_bonus = max(0, (max_days - distinct_days)) * weights.get('compactness_reward', 0.0)
    score += compactness_bonus
    if avg_rating is not None:
        score += avg_rating * weights.get('rating_weight', 5.0) * len(courses)

    # apply preference penalties/rewards
    pref_penalties = []
    if unavailable_days:
        udays = set(unavailable_days.upper())
        for c in courses:
            if getattr(c, 'days_of_week', None) and udays & set(c.days_of_week.upper()):
                penalty = weights.get('unavailable_day_penalty', 500.0)
                score -= penalty
                pref_penalties.append({'course': getattr(c, 'course_code', None), 'reason': 'unavailable_day', 'penalty': penalty})

    if avoid_mornings:
        # penalize courses that start before 10:00
        for c in courses:
            st = _to_time_obj(getattr(c, 'start_time', None))
            if st and st.hour < 10:
                penalty = weights.get('avoid_morning_penalty', 150.0)
                score -= penalty
                pref_penalties.append({'course': getattr(c, 'course_code', None), 'reason': 'avoid_morning', 'penalty': penalty})

    if avoid_evenings:
        # penalize courses that end after 18:00
        for c in courses:
            et = _to_time_obj(getattr(c, 'end_time', None))
            if et and et.hour >= 18:
                penalty = weights.get('avoid_evening_penalty', 150.0)
                score -= penalty
                pref_penalties.append({'course': getattr(c, 'course_code', None), 'reason': 'avoid_evening', 'penalty': penalty})

    if preferred_instructors:
        for c in courses:
            instr = getattr(c, 'instructor', None)
            if instr and instr.strip().lower() in preferred_instructors:
                reward = weights.get('preferred_instructor_reward', 75.0)
                score += reward
                pref_penalties.append({'course': getattr(c, 'course_code', None), 'reason': 'preferred_instructor', 'reward': reward})

    return {
        'score': score,
        'breakdown': {
            'base': weights.get('base', 0.0),
            'conflict_count': conflict_count,
            'conflicts': conflicts,
            'total_gaps_minutes': total_gaps_minutes,
            'distinct_days': distinct_days,
            'compactness_bonus': compactness_bonus,
            'avg_rating': avg_rating,
            'preference_adjustments': pref_penalties
        },
        'weights': weights
    }


def score_schedule(course_ids: List[int], db, weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    # fetch courses from db and score
    # Import Course model dynamically to avoid circular import issues
    from tables.course import Course as CourseModel
    courses = db.query(CourseModel).filter(CourseModel.id.in_(course_ids)).all()
    if len(courses) != len(course_ids):
        return {'error': 'One or more courses not found', 'requested': len(course_ids), 'found': len(courses)}
    return score_courses(courses, weights=weights, db=db)
