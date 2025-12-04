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
