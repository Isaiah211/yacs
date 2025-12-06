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
    is_hidden = Column(Boolean, nullable=False, default=False)
    flag_count = Column(Integer, nullable=False, default=0)
    flagged_reason = Column(Text, nullable=True)
    flagged_by = Column(String(255), nullable=True)
    flagged_at = Column(DateTime(timezone=True), nullable=True)
    moderation_notes = Column(Text, nullable=True)
    moderated_by = Column(String(255), nullable=True)
    moderated_at = Column(DateTime(timezone=True), nullable=True)

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
            'is_hidden': self.is_hidden,
            'flag_count': self.flag_count,
            'flagged_reason': self.flagged_reason,
            'flagged_by': self.flagged_by,
            'flagged_at': self.flagged_at.isoformat() if self.flagged_at else None,
            'moderation_notes': self.moderation_notes,
            'moderated_by': self.moderated_by,
            'moderated_at': self.moderated_at.isoformat() if self.moderated_at else None,
        }
