from sqlalchemy import Column, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship

from .database import Base

class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisite"

    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    prerequisite_id = Column(Integer, ForeignKey('courses.id'), nullable=False)

    course = relationship("Course", foreign_keys=[course_id], backref="prerequisites")
    prerequisite = relationship("Course", foreign_keys=[prerequisite_id])

    __table_args__ = (
        PrimaryKeyConstraint('course_id', 'prerequisite_id'),
    )
