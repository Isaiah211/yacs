from types import SimpleNamespace
from services.score import score_courses


def make_course(code, days, start, end, cid=0, semester='Fall 2025'):
    return SimpleNamespace(id=cid, course_code=code, days_of_week=days, start_time=start, end_time=end, semester=semester)


def test_no_conflicts_low_gaps():
    c1 = make_course('CSCI-1000', 'MWF', '09:00:00', '09:50:00', cid=1)
    c2 = make_course('MATH-1010', 'TR', '10:00:00', '11:15:00', cid=2)
    res = score_courses([c1, c2])
    assert 'score' in res
    assert res['breakdown']['conflict_count'] == 0


def test_conflict_detected():
    c1 = make_course('CSCI-1000', 'MWF', '09:00:00', '10:00:00', cid=1)
    c2 = make_course('PHYS-2000', 'MWF', '09:30:00', '10:30:00', cid=2)
    res = score_courses([c1, c2])
    assert res['breakdown']['conflict_count'] == 1
