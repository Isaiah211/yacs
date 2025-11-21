from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import relationship

from .database import Base


class CourseReview(Base):
    __tablename__ = 'course_reviews'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False, index=True)
    semester = Column(String(20), nullable=True)
    user_identifier = Column(String(255), nullable=True)
    user_name = Column(String(255), nullable=True)
    rating = Column(Integer, nullable=False)
    difficulty = Column(Integer, nullable=True)
    workload_hours = Column(Integer, nullable=True)
    would_recommend = Column(Boolean, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    course = relationship('Course', backref='reviews')

    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'course_code': self.course.course_code if self.course else None,
            'semester': self.semester,
            'user_identifier': self.user_identifier,
            'user_name': self.user_name,
            'rating': self.rating,
            'difficulty': self.difficulty,
            'workload_hours': self.workload_hours,
            'would_recommend': self.would_recommend,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
