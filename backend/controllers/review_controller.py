from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from tables.course import Course
from tables.course_review import CourseReview
from services import review_analytics


def create_review(payload: Dict[str, Any], db: Session):
    # payload expected to include 'course_code' and review fields
    course_code = payload.get('course_code')
    if not course_code:
        return {'error': 'course_code required'}, 400

    course = db.query(Course).filter(Course.course_code == course_code).first()
    if not course:
        return {'error': 'Course not found'}, 404

    review = CourseReview(
        course_id=course.id,
        semester=payload.get('semester'),
        user_identifier=payload.get('user_identifier'),
        user_name=payload.get('user_name'),
        rating=payload.get('rating', 0),
        difficulty=payload.get('difficulty'),
        workload_hours=payload.get('workload_hours'),
        would_recommend=payload.get('would_recommend'),
        comment=payload.get('comment')
    )

    db.add(review)
    db.commit()
    db.refresh(review)
    return review.to_dict()


def list_reviews(db: Session, course_code: str, semester: Optional[str] = None, limit: int = 50, offset: int = 0):
    course = db.query(Course).filter(Course.course_code == course_code).first()
    if not course:
        return {'error': 'Course not found'}, 404

    q = db.query(CourseReview).filter(CourseReview.course_id == course.id)
    if semester:
        q = q.filter(CourseReview.semester == semester)
    q = q.order_by(CourseReview.created_at.desc()).limit(limit).offset(offset)
    reviews = q.all()
    return [r.to_dict() for r in reviews]


def get_review(review_id: int, db: Session):
    r = db.query(CourseReview).get(review_id)
    if not r:
        return {'error': 'Review not found'}, 404
    return r.to_dict()


def update_review(review_id: int, updates: Dict[str, Any], db: Session):
    r = db.query(CourseReview).get(review_id)
    if not r:
        return {'error': 'Review not found'}, 404

    for k, v in updates.items():
        if hasattr(r, k):
            setattr(r, k, v)

    db.add(r)
    db.commit()
    db.refresh(r)
    return r.to_dict()


def delete_review(review_id: int, db: Session):
    r = db.query(CourseReview).get(review_id)
    if not r:
        return {'error': 'Review not found'}, 404
    db.delete(r)
    db.commit()
    return {'success': True}


def get_course_rating_summary(db: Session, course_code: str, semester: Optional[str] = None):
    course = db.query(Course).filter(Course.course_code == course_code).first()
    if not course:
        return {'error': 'Course not found'}, 404

    q = db.query(CourseReview).filter(CourseReview.course_id == course.id)
    if semester:
        q = q.filter(CourseReview.semester == semester)

    reviews: List[CourseReview] = q.all()
    if not reviews:
        return {
            'course_code': course_code,
            'course_title': getattr(course, 'title', None),
            'review_count': 0,
            'average_rating': None,
            'average_difficulty': None,
            'average_workload': None,
            'recommend_rate': None,
            'analytics': review_analytics.analyze_comments([])
        }

    ratings = [r.rating for r in reviews if r.rating is not None]
    difficulties = [r.difficulty for r in reviews if r.difficulty is not None]
    workloads = [r.workload_hours for r in reviews if r.workload_hours is not None]
    recommends = [1 if r.would_recommend else 0 for r in reviews if r.would_recommend is not None]

    comments = [r.comment for r in reviews if r.comment]

    analytics = review_analytics.analyze_comments(comments)

    return {
        'course_code': course_code,
        'course_title': getattr(course, 'title', None),
        'review_count': len(reviews),
        'average_rating': sum(ratings) / len(ratings) if ratings else None,
        'average_difficulty': sum(difficulties) / len(difficulties) if difficulties else None,
        'average_workload': sum(workloads) / len(workloads) if workloads else None,
        'recommend_rate': (sum(recommends) / len(recommends)) if recommends else None,
        'analytics': analytics
    }


def get_top_rated_courses(db: Session, semester: Optional[str] = None, department: Optional[str] = None, min_reviews: int = 3, limit: int = 10):
    # Aggregate average rating per course and return top results
    from sqlalchemy import func

    q = db.query(
        Course.id,
        Course.course_code,
        Course.title,
        func.count(CourseReview.id).label('review_count'),
        func.avg(CourseReview.rating).label('avg_rating')
    ).join(CourseReview, CourseReview.course_id == Course.id)

    if semester:
        q = q.filter(CourseReview.semester == semester)
    if department:
        q = q.filter(Course.department == department)

    q = q.group_by(Course.id).having(func.count(CourseReview.id) >= min_reviews).order_by(func.avg(CourseReview.rating).desc()).limit(limit)

    results = q.all()
    return [
        {'course_code': r.course_code, 'title': r.title, 'review_count': r.review_count, 'average_rating': float(r.avg_rating)}
        for r in results
    ]
