from typing import Dict, List, Optional

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from ..tables.course import Course
from ..tables.course_review import CourseReview


def _resolve_course(db: Session, course_id: Optional[int] = None, course_code: Optional[str] = None, semester: Optional[str] = None) -> Optional[Course]:
    query = db.query(Course)

    if course_id is not None:
        return query.filter(Course.id == course_id).first()

    if course_code:
        query = query.filter(Course.course_code == course_code)
        if semester:
            query = query.filter(Course.semester == semester)
        return query.first()

    return None

def create_review(review_data: Dict, db: Session) -> Dict:
    try:
        course = _resolve_course(db, course_id=review_data.get("course_id"), course_code=review_data.get("course_code"), semester=review_data.get("semester"))

        if not course:
            return {"success": False, "error": "Course not found"}

        new_review = CourseReview(
            course_id=course.id,
            semester=review_data.get("semester") or course.semester,
            user_identifier=review_data.get("user_identifier"),
            user_name=review_data.get("user_name"),
            rating=review_data["rating"],
            difficulty=review_data.get("difficulty"),
            workload_hours=review_data.get("workload_hours"),
            would_recommend=review_data.get("would_recommend"),
            comment=review_data.get("comment"),
        )

        db.add(new_review)
        db.commit()
        db.refresh(new_review)

        return {
            "success": True,
            "message": "Review created successfully",
            "review": new_review.to_dict()
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

def list_reviews(db: Session, course_id: Optional[int] = None, course_code: Optional[str] = None, semester: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict:
    try:
        query = db.query(CourseReview).join(Course)

        if course_id is not None:
            query = query.filter(CourseReview.course_id == course_id)
        elif course_code:
            query = query.filter(Course.course_code == course_code)
            if semester:
                query = query.filter(CourseReview.semester == semester)
        elif semester:
            query = query.filter(CourseReview.semester == semester)

        total = query.count()
        reviews = query.order_by(CourseReview.created_at.desc()).limit(limit).offset(offset).all()

        return {
            "success": True,
            "reviews": [review.to_dict() for review in reviews],
            "metadata": {
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_review(review_id: int, db: Session) -> Dict:
    try:
        review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
        if not review:
            return {"success": False, "error": "Review not found"}
        return {"success": True, "review": review.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_review(review_id: int, updates: Dict, db: Session) -> Dict:
    try:
        review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
        if not review:
            return {"success": False, "error": "Review not found"}

        for field in [
            "rating",
            "difficulty",
            "workload_hours",
            "would_recommend",
            "comment",
            "user_name"
        ]:
            if field in updates and updates[field] is not None:
                setattr(review, field, updates[field])

        db.commit()
        db.refresh(review)
        return {"success": True, "review": review.to_dict()}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

def delete_review(review_id: int, db: Session) -> Dict:
    try:
        review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
        if not review:
            return {"success": False, "error": "Review not found"}

        db.delete(review)
        db.commit()
        return {"success": True, "message": "Review deleted"}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

def get_course_rating_summary(db: Session, course_id: Optional[int] = None, course_code: Optional[str] = None, semester: Optional[str] = None) -> Dict:
    try:
        query = db.query(
            func.count(CourseReview.id).label('count'),
            func.avg(CourseReview.rating).label('avg_rating'),
            func.avg(CourseReview.difficulty).label('avg_difficulty'),
            func.avg(CourseReview.workload_hours).label('avg_workload'),
            func.sum(case((CourseReview.would_recommend == True, 1), else_=0)).label('recommendations')
        ).join(Course)

        if course_id is not None:
            query = query.filter(CourseReview.course_id == course_id)
        elif course_code:
            query = query.filter(Course.course_code == course_code)
        if semester:
            query = query.filter(CourseReview.semester == semester)

        result = query.first()
        count = result.count if result and result.count else 0

        if count == 0:
            return {
                "success": True,
                "summary": {
                    "count": 0,
                    "average_rating": None,
                    "average_difficulty": None,
                    "average_workload": None,
                    "recommendation_rate": None
                }
            }

        recommend_rate = None
        if result.recommendations is not None and count > 0:
            recommend_rate = float(result.recommendations)/count

        return {
            "success": True,
            "summary": {
                "count": count,
                "average_rating": round(float(result.avg_rating), 2) if result.avg_rating else None,
                "average_difficulty": round(float(result.avg_difficulty), 2) if result.avg_difficulty else None,
                "average_workload": round(float(result.avg_workload), 2) if result.avg_workload else None,
                "recommendation_rate": round(recommend_rate, 2) if recommend_rate is not None else None
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_top_rated_courses(db: Session, semester: Optional[str] = None, department: Optional[str] = None, min_reviews: int = 3, limit: int = 10) -> Dict:
    try:
        query = db.query(
            Course.id.label('course_id'),
            Course.course_code,
            Course.name,
            Course.department,
            Course.semester,
            func.count(CourseReview.id).label('count'),
            func.avg(CourseReview.rating).label('avg_rating')
        ).join(CourseReview, Course.id == CourseReview.course_id)

        if semester:
            query = query.filter(CourseReview.semester == semester)
        if department:
            query = query.filter(Course.department == department)

        query = (
            query.group_by(Course.id)
            .having(func.count(CourseReview.id) >= min_reviews)
            .order_by(func.avg(CourseReview.rating).desc())
            .limit(limit)
        )

        rows = query.all()
        return {
            "success": True,
            "courses": [
                {
                    "course_id": row.course_id,
                    "course_code": row.course_code,
                    "name": row.name,
                    "department": row.department,
                    "semester": row.semester,
                    "review_count": row.count,
                    "average_rating": round(float(row.avg_rating), 2) if row.avg_rating else None
                }
                for row in rows
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
