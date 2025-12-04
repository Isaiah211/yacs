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


def test_preferences_avoid_mornings():
    # morning class vs afternoon class; user prefers to avoid mornings
    morning = make_course('CSCI-1100', 'MWF', '08:30:00', '09:45:00', cid=10)
    afternoon = make_course('HIST-2000', 'TR', '13:00:00', '14:15:00', cid=11)

    prefs = {'avoid_mornings': True}

    score_morning = score_courses([morning], preferences=prefs)
    score_afternoon = score_courses([afternoon], preferences=prefs)

    # afternoon schedule should score higher because morning is penalized
    assert score_afternoon['score'] > score_morning['score']


def test_preferences_earliest_start_window():
    # user requires classes not to start before 10:00
    early = make_course('ENG-1000', 'MWF', '09:00:00', '10:00:00', cid=20)
    ok = make_course('ENG-1010', 'MWF', '10:30:00', '11:45:00', cid=21)

    prefs = {'earliest_start_time': '10:00:00'}

    score_early = score_courses([early], preferences=prefs)
    score_ok = score_courses([ok], preferences=prefs)

    assert score_ok['score'] > score_early['score']
