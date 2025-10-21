from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from .model import Base

class Course(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True)
    course_code = Column(String(10), unique=True, nullable=False)  # e.g., "CSCI-1200"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    credits = Column(Integer, nullable=False)
    semester = Column(String(20), nullable=False)  # e.g., "Fall 2025"
    department = Column(String(50), nullable=False)
    prerequisites = Column(String(255), nullable=True)
    capacity = Column(Integer, nullable=True)
    instructor = Column(String(100), nullable=True)

    def to_dict(self):
        """Convert course object to dictionary"""
        return {
            'id': self.id,
            'course_code': self.course_code,
            'name': self.name,
            'description': self.description,
            'credits': self.credits,
            'semester': self.semester,
            'department': self.department,
            'prerequisites': self.prerequisites,
            'capacity': self.capacity,
            'instructor': self.instructor
        }