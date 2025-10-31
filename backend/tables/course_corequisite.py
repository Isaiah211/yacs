from sqlalchemy import Column, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship

from .database import Base

class CourseCorequisite(Base):
    __tablename__ = 'course_corequisite'

    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    corequisite_id = Column(Integer, ForeignKey('courses.id'), nullable=False)

    course = relationship("Course", foreign_keys=[course_id], backref="corequisites")
    corequisite = relationship("Course", foreign_keys=[corequisite_id])

    __table_args__ = (
        PrimaryKeyConstraint('course_id', 'corequisite_id'),
    )